# coding: utf8

import re
import sys
import inspect
import logging
import os
from werkzeug.debug import DebuggedApplication
from werkzeug.serving import run_simple
from werkzeug.contrib.sessions import SessionMiddleware, FilesystemSessionStore
from werkzeug.contrib.lint import LintMiddleware
from werkzeug.contrib.profiler import ProfilerMiddleware
from werkzeug.exceptions import NotFound, HTTPException
from jinja2.environment import Environment
from jinja2.loaders import FileSystemLoader
from controller import XController
from xweb.util import logging
from web import XRequest
from xweb.config import XConfig
from werkzeug.exceptions import BadRequest, abort


re.compile("\(\?P<([^>]+)>\)")
keys_regex = re.compile('<([^|>]+)(?:\|([^>]+))?>', re.DOTALL)

session_store = FilesystemSessionStore()


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
        

class XWeb:
    app = None

class XApplication:
    '''
    Application类
    '''
    def __init__(self, sub_app_name, base_path=''):
        
        
        self.rewrite_rules = []
        self.loadConfig()

        self.sub_app_name = sub_app_name
        self.use_debuger = False
        if base_path:
            template_path = "%s/%s/templates" % (base_path, self.sub_app_name)
        else:
            template_path = "%s/templates" % (self.sub_app_name)

        logging.info('base_path %s template_path %s' , base_path, template_path)

        if not os.path.isdir(template_path):
            raise Exception('template_path %s not found' % template_path)

    
        self.jinja_env = Environment(loader=FileSystemLoader(template_path), autoescape=True)
        
        controller_module_path = "%s.controller" % sub_app_name
        app_module = sys.modules.get(controller_module_path)
        
        if not app_module:
            try:
                app_module = __import__(controller_module_path)
                self.controller_module = app_module.controller
            except:
                raise Exception("Error in importing controller module, app startup failed")
            
        XWeb.app = self
            
    def rewrite(self, environ):
        
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
        
        controller  = request.get('c')
        action      = request.get('a')

        if controller and action:
            controller = controller.lower()
            action     = action.lower()

            try:

                controller_class_name = controller.title().replace('_', '') + 'Controller'
                if not hasattr(self.controller_module, controller_class_name):
                    return BadRequest('Controller NOT FOUND')
                    
                controller_class = getattr(self.controller_module, controller_class_name)

                controller_instance = controller_class(request, self)
                
                if not isinstance(controller_instance, XController):
                    return BadRequest('Controller Type Error')

                action_method_name = 'do%s'%action.title()
                
                if not hasattr(controller_instance, action_method_name):
                    return BadRequest('Method NOT FOUND')
                
                action_method = getattr(controller_instance, action_method_name)
                if not callable(action_method):
                    return BadRequest('%s.%s is not callable', controller_class_name, action_method_name)
                
                spec = inspect.getargspec(action_method.__func__)
                func_args = spec.args
                defaults = spec.defaults
                
                kwargs = {}
                if defaults and func_args:
                    func_args = list(func_args)
                    defaults = list(defaults)
                    
                    for i in range(len(func_args)-len(defaults)): #@UnusedVariable
                        defaults.insert(0, None)
                            
                    for func_arg, arg in zip(func_args, defaults):
                        if not self.request.args.has_key(func_arg):
                            kwargs[func_arg] = arg
                        else:
                            kwargs[func_arg] = request.args.get(func_args)
                    
            except ImportError, AttributeError: #@ReservedAssignment
                logging.exception("Can't find the method to process")
                return BadRequest('%s is not callable', action_method_name)
                
            except Exception as ex:
                logging.exception(ex)
                return self.handleException(controller=controller, action=action, ex=ex)             
           
            unitofwork = controller_instance.unitofwork
            try:
                controller_instance.beforeAction()       
                action_method(**kwargs)
                controller_instance.afterAction()
                
                if not unitofwork.commit():
                    raise Exception("commit error")
                
                context = controller_instance.context
                content_type = controller_instance.content_type
                status_code = controller_instance.response.status_code
                
                if status_code == 200:
                    if content_type == 'json':
                        controller_instance.response.data = context.get('json') or ''
                    elif content_type == 'string':
                        controller_instance.response.data = context.get('string') or ''
                    else:
                        
                        if hasattr(controller_instance, 'template') and controller_instance.template:
                            template_name = controller_instance.template
                        else:
                            template_name = "%s/%s.html" % (controller, action)
                            
                        if hasattr(controller_instance, 'render') and callable(controller_instance.render):
                            controller_instance.response.data = controller_instance.render(action=action)
                        else:
                            controller_instance.response.data = self.render(template_name, context)
                else:
                    return abort(status_code, context.get('description'))
            except Exception, ex:
                if hasattr(controller_instance, 'handleException') and callable(controller_instance.handleException):
                    kwargs['action'] = action
                    kwargs['ex'] = ex
                    controller_instance.handleException(**kwargs)
                else:
                    if self.use_debuger:
                        raise
                    else:
                        logging.exception("error in process action")
                        return self.handleException(controller, action, ex)
            
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
        app = SessionMiddleware(app, FilesystemSessionStore())
        #app = ProfilerMiddleware(app)
        
        return app
    
    def runApp(self, environ, start_response):
        response = None
        try:
            request = self.rewrite(environ)
            response = self.process(request)
            request.secure_cookies.save_cookie(response)
        except HTTPException, ex:
            response = ex
        
        if response:
            return response(environ, start_response)
        
    def loadConfig(self):
        try:
            if not self.rewrite_rules:
                rules = XConfig.get('rewrite_rules')
                if isinstance(rules, list):
                    self.buildRewrite(rules)
        except:
            pass
        
        return self
        
    def buildRewrite(self, rules):
        self.rewrite_rules = []
        for rule in rules:
            self.rewrite_rules.append(XRewriteRule(*rule))
            
        self.rewrite_rules.extend([
            XRewriteRule('/',                  {'c':'default', 'a':'index'}),
            XRewriteRule('/<c>/',              {'a':'index'}),
            XRewriteRule('/<c>/<a>/',          {}),
        ])
        
    def createUrl(self, route, params):
        for rule in self.rewrite_rules:
            url = rule.createUrl(route, params)
            
            if url:
                return url
            
        return ''
        
    def run(self):
        run_simple('0.0.0.0', 5000, self.runApp, use_reloader=True, use_debugger=True)    
        
    def runDebug(self):
        self.use_debuger = True
        app = DebuggedApplication(self.createApp(), evalex=True)
        run_simple('0.0.0.0', 5000, app, use_reloader=True, use_debugger=True)
