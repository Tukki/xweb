# coding: utf-8
import re
import sys
import inspect
import os
import time
import json

from werkzeug.debug import DebuggedApplication
from werkzeug.serving import run_simple, make_server
from werkzeug.contrib.sessions import SessionMiddleware
from werkzeug.wsgi import SharedDataMiddleware
from werkzeug.contrib.lint import LintMiddleware
from werkzeug.contrib.profiler import ProfilerMiddleware
from werkzeug.exceptions import NotFound, HTTPException, BadRequest, abort

from jinja2.environment import Environment
from jinja2.loaders import FileSystemLoader

from controller import XController
from web import XRequest
from xweb.util import logging, BlockProfiler
from xweb.config import XConfig
from xweb.orm import UnitOfWork
from xweb.orm.unitofwork import DBError

re.compile("\(\?P<([^>]+)>\)")
keys_regex = re.compile('<([^|>]+)(?:\|([^>]+))?>', re.DOTALL)

class XRewriteRule:
    
    def __init__(self, regex, params):
        self.params = params
        self.keys = {}
        keys = keys_regex.findall(regex)
        
        for key, value in keys:
            self.keys[key] = re.compile('^%s$' % value if value else '[^/]+')
        
        def func(m):
            if not m.group(2):
                return "(?P<%s>[^/]+)"%m.group(1)
            else:
                return "(?P<%s>%s)"%(m.group(1), m.group(2))
            
        pattern = "^%s$"%keys_regex.sub(func, regex)
        self.pattern = re.compile(pattern)
        self.urlfor = keys_regex.sub('%(\g<1>)s', regex)
        self.regex = regex
        
    def parseUrl(self, path_info):
        if not self.pattern.match(path_info):
            return None
        
        match = self.pattern.search(path_info)
        
        params = []
        
        for k in match.groupdict():
            v = match.groupdict().get(k)
            params.append("%s=%s" % (k, v) )
            
        for k in self.params:
            params.append("%s=%s" % (k, self.params.get(k)) )

        return "&".join(params)
        
        
    def createUrl(self, route, params):
        assert isinstance(params, dict)
        
        controller, action = route.strip().split("/")

        params['c'] = controller
        params['a'] = action
        
        for key in self.keys:
            pattern = self.keys.get(key)
            
            param = params.get(key)
            
            if not param:
                return False
            
            if not pattern.match(str(param)):
                return False
            
            
        for key in self.params:
            
            param = params.get(key)
            
            if param is not None and param != self.params.get(key):
                return False
            
            
        default = {}
        more = []
        
        
        for key in params:
            if key in self.params:
                continue
            
            pattern = self.keys.get(key)
            
            if not pattern:
                more.append( "%s=%s" % (key, params.get(key)))
            else:
                default[key] = params.get(key)
                
                
        url = self.urlfor % default
        
        if not more:
            return url
        
        if url.find("?")>-1:
            return url + "&" + "&".join(more)
        else:
            return url + "?" + "&".join(more)
        

class XApplication(object):
    '''
    Application类
    @author: lifei <lifei@7v1.net>
    '''

    CONTROLLERS = {}
    
    def __init__(self, sub_app_name, base_path='', static_root='static'):

        self.sub_app_name = sub_app_name
        self.use_debuger = False
        
        if not base_path:
            self.base_path = '.'
        else:
            if base_path.endswith("/"):
                self.base_path = base_path[:-1]
            else:
                self.base_path = base_path
                
        self.base_path = os.path.abspath(self.base_path)
                
        template_path = "%s/%s/templates" % (self.base_path, self.sub_app_name)
        if not os.path.isdir(template_path):
            raise Exception('template_path %s not found' % template_path)
        
        self.jinja_env = Environment(loader=FileSystemLoader(template_path), autoescape=True)
        
        self.rewrite_rules = []
        self.createRewriteRules()
        self.static_root = static_root
            
    def createRequest(self, environ):
        
        for rule in self.rewrite_rules:
            path_info = environ.get('PATH_INFO', '/')
            q = rule.parseUrl(path_info)
            if q is not None:
                if environ['QUERY_STRING']:
                    environ['QUERY_STRING'] += '&'+q
                else:
                    environ['QUERY_STRING'] = q
                    
                break
        
        return XRequest(environ, populate_request=False)
        
    def process(self, request):
        
        logging.update()
        controller  = request.get('c')
        action      = request.get('a')

        if controller and action:
            controller = controller.lower()
            action     = action.lower()

            try:
                
                controller_class_name = controller.title().replace('_', '') + 'Controller'
                if not XApplication.CONTROLLERS.has_key(controller_class_name):
                    return BadRequest('CONTROLLER NOT FOUND %s' % controller_class_name)
                    
                controller_class = XApplication.CONTROLLERS[controller_class_name]
                if not issubclass(controller_class, XController):
                    return BadRequest('BAD CONTROLLER CLASS')
                    
                controller_instance = controller_class(request, self)
                if not isinstance(controller_instance, XController):
                    return BadRequest('BAD CONTROLLER INSTANCE')

                action_method_name = 'do%s'%action.replace('_', '')
                if not hasattr(controller_instance, action_method_name):
                    return BadRequest('METHOD NOT FOUND %s' % action_method_name)
                
                action_method = getattr(controller_instance, action_method_name)
                if not callable(action_method):
                    return BadRequest('%s.%s is not callable' %(controller_class_name, action_method_name) )
                
                kwargs = {}
                spec = inspect.getargspec(action_method)
                func_args = spec.args[1:]
                
                for k in func_args:
                    if request.args.has_key(k):
                        kwargs[k] = request.args.get(k)
                
                # 由函数的默认值获取配置信息
                if spec.defaults:
                    defaults = dict(zip(func_args[-(len(spec.defaults)):], spec.defaults))
                    
                    mimetype = defaults.get('mimetype')
                    if mimetype:
                        controller_instance.mimetype = mimetype
                        
                    charset = defaults.get('charset')
                    if charset in ['gbk', 'utf-8', 'iso-9001']:
                        controller_instance.response.charset = charset
                    
                    read_only = defaults.get('read_only')
                    if read_only is not None:
                        controller_instance.read_only = read_only
                        
                    use_cache = defaults.get('use_cache')
                    if use_cache is not None:
                        controller_instance.use_cache = use_cache
                    
                    status_code = defaults.get('status_code')
                    if status_code:
                        controller_instance.response.status_code = status_code
                        
            except (ImportError, AttributeError) as ex:
                logging.exception("Can't find the method to process")
                return BadRequest('SEARCH METHOD ERROR %s' % ex)
                
            except Exception as ex:
                logging.exception(ex)
                return self.handleException(controller=controller, action=action, ex=ex)             
           
            try:
                controller_instance.action = action
                
                with BlockProfiler("[XWEB] ACTION EXECTION"):
                    if controller_instance.beforeAction():
                        action_method(**kwargs)
                        controller_instance.afterAction()
                        if not controller_instance.commit():
                            if hasattr(controller_instance, 'handleCommentFail') \
                                and callable(controller_instance.handleCommentFail):
                                return controller_instance.handleCommentFail()
                            return abort(500, 'COMMENT FAILED')
                
                context = controller_instance.context
                content_type = controller_instance.content_type
                status_code = controller_instance.response.status_code
                
                if status_code == 200:
                    if content_type == 'json':
                        controller_instance.response.data = json.dumps(getattr(controller_instance, 'json', ''))
                    elif content_type == 'text':
                        pass
                    else:
                        
                        if hasattr(controller_instance, 'template') and controller_instance.template:
                            template_name = controller_instance.template
                        else:
                            template_name = "%s/%s.html" % (controller, action)
                        
                        if hasattr(controller_instance, 'render') and callable(controller_instance.render):
                            controller_instance.response.data = controller_instance.render(action=action)
                        else:
                            controller_instance.response.data = self.render(template_name, context)
                elif status_code in [301, 302]:
                    pass
                else:
                    return abort(status_code, context.get('description'))
            except Exception, ex:
                if self.use_debuger:
                    raise
                if hasattr(controller_instance, 'handleException') and callable(controller_instance.handleException):
                    kwargs['action'] = action
                    kwargs['ex'] = ex
                    controller_instance.handleException(**kwargs)
                else:
                    logging.exception("error in process action")
                    return self.handleException(controller, action, ex)
                    
            finally:
                controller_instance.afterRender()
            
            return controller_instance.response
        
        return NotFound()
    
    def render(self, template_name, context):
        '''
        @note: override
        '''
        t = self.jinja_env.get_template(template_name)
        return t.render(context)
    
    def handleException(self, controller, action, ex):
        return BadRequest(ex)
    
    def createApp(self):
        app = self.runApp
        #app = SessionMiddleware(app, FilesystemSessionStore())
        #app = ProfilerMiddleware(app)
        
        return app
    
    def runApp(self, environ, start_response):
        response = None
        t = time.time()
        try:
            request = self.createRequest(environ)
            response = self.process(request)
            request.secure_cookies.save_cookie(response)
        except HTTPException, ex:
            response = ex
            
        t = (time.time() - t) * 1000
        logging.debug("Request time: %.2f ms" % t)
        
        return response(environ, start_response)
        
    def createRewriteRules(self):
        self.rewrite_rules.extend([
            XRewriteRule('/',                  {'c':'default', 'a':'index'}),
            XRewriteRule('/<c>/',              {'a':'index'}),
            XRewriteRule('/<c>/<a>/',          {}),
        ])
        
        return self
        
    def buildRewrite(self, rules):
        self.rewrite_rules = []
        for rule in rules:
            self.rewrite_rules.append(XRewriteRule(*rule))
        
    def createUrl(self, route, **params):
        '''创建基于XWEB MVC规则的URL
        
        @param route: 访问的route，格式为 <controller>/<action>
        @param param: 相应的参数
        '''
        for rule in self.rewrite_rules:
            url = rule.createUrl(route, params)
            
            if url:
                return url
            
        return ''
        
    def run(self):
        run_simple('0.0.0.0', 5000, self.runApp, threaded=True)    
        
    def runDebug(self, port=5000):
        import thread
        thread.start_new_thread(self._reload, ())
        self.use_debuger = True
        app = self.runApp
        
        app = SharedDataMiddleware(app, {
            '/static': self.static_root
        })
        app = DebuggedApplication(app, evalex=True)
        run_simple('0.0.0.0', port, app, use_debugger=True, threaded=True)
        
    def _reload(self):
        mtimes = {}
        
        while 1: 
            try:
                has_reload = False
                sub_modules = set()
                for filename, module, k in _iter_module_files():
                    
                    filename = os.path.abspath(filename)
                    
                    try:
                        mtime = os.stat(filename).st_mtime
                    except OSError:
                        continue
                    
                    if filename.find(self.base_path)== -1:
                        continue
                    
                    sub_modules.add(k)
                    old_time = mtimes.get(filename)
                    if old_time is None:
                        mtimes[filename] = mtime
                        continue
                    elif mtime > old_time:
                        mtimes[filename] = mtime
                        if module.__name__ in ['__main__']:
                            continue
                        
                        reload(module)
                        has_reload = True
                        logging.info(' * Detected change in %r, reloading', filename)
                
                if has_reload:
                    for k in sub_modules:
                        
                        if k in ['__main__'] or k not in sys.modules:
                            continue
                        del sys.modules[k]
                    
                    #self.importModule('controller')
                    for cls in XApplication.CONTROLLERS.values():
                        __import__(cls.__module__)
                        
            except:
                logging.exception("reload error")
            finally:
                time.sleep(1)


def _iter_module_files():
    for k in sys.modules.keys():
        module = sys.modules.get(k)
        filename = getattr(module, '__file__', None)
        if filename:
            old = None
            while not os.path.isfile(filename):
                old = filename
                filename = os.path.dirname(filename)
                if filename == old:
                    break
            else:
                if filename[-4:] in ('.pyc', '.pyo'):
                    filename = filename[:-1]
                elif filename[-9:] == '$py.class':
                    filename = "%s.py" % filename[:-9]
                elif filename[-4:] == '.jar':
                    continue
                    
                yield filename, module, k
                
