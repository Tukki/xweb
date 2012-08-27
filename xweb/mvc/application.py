# coding: utf8

import re
import logging
import sys
import inspect
from werkzeug.debug import DebuggedApplication #@UnresolvedImport
from werkzeug.serving import run_simple #@UnresolvedImport
from werkzeug.wrappers import BaseResponse
from werkzeug.utils import redirect
from werkzeug.exceptions import NotFound, HTTPException #@UnresolvedImport
from jinja2.environment import Environment
from jinja2.loaders import FileSystemLoader
from controller import XController
from web import XRequest, XResponse
from xweb.config import XConfig


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
        


class XApplication:
    '''
    Application类
    '''
    
    def __init__(self, app_name):
        self.rewrite_rules = []
        self.loadConfig()
        self.app_name = app_name
        
        controller_module_path = "%s.controller" % app_name
        app_module = sys.modules.get(controller_module_path)
        
        if not app_module:
            try:
                app_module = __import__(controller_module_path)
                self.controller_module = app_module.controller
            except:
                raise Exception("Error in importing controller module, app startup failed")
            
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
            action  = action.lower()

            try:

                controller_class_name = controller.title().replace('_', '') + 'Controller'
                if not hasattr(self.controller_module, controller_class_name):
                    return NotFound()
                    
                controller_class = getattr(self.controller_module, controller_class_name)

                controller_instance = controller_class(request)

                if isinstance(controller_instance, XController):
                    action_method_name = 'do%s'%action.title()
                    
                    if not hasattr(controller_instance, action_method_name):
                        return NotFound()
                    
                    action_method = getattr(controller_instance, action_method_name)
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
                    
                    unitofwork = controller_instance.unitofwork
                    try:
                        controller_instance.before()       
                        action_method(**kwargs)
                        controller_instance.after()
                        
                        if not unitofwork.commit():
                            raise Exception("commit error")
                        
                        context = controller_instance.context

                        if context['code'] == 200:
                            if context['type'] == 'json':
                                return XResponse(context['json'],   mimetype='application/json')
                            elif context['type'] == 'string':
                                return XResponse(context['string'], mimetype='text/html')
                            else:
                                template_path = "%s/templates/%s" % (self.app_name, controller)
                                jinja_env = Environment(loader=FileSystemLoader(template_path), autoescape=True)
                                t = jinja_env.get_template(action + '.html')
                                return XResponse(t.render(context), mimetype='text/html')
                        elif context['code'] == 302 or context['code'] == 301:
                            return redirect(context['url'], context['code'])
                        elif context['code'] == 404:
                            return NotFound()
                        else:
                            response = BaseResponse(
                                '', context['code'] or 404, mimetype='text/html')
                            return response
                    except Exception as ex:
                        logging.exception("error in process action")
                        return BaseResponse(str(ex), 500, mimetype='text/html')
                    finally:
                        unitofwork.reset()
                    
            except ImportError, AttributeError:
                logging.exception("Can't find the method to process")
                return NotFound()
                
            except Exception as ex:
                logging.exception(ex)
                return XResponse(str(ex), mimetype='text/html')
        
        return NotFound()
    
    def createApp(self):
        return self.runApp
    
    def runApp(self, environ, start_response):
        response = None
        try:
            request = self.rewrite(environ)
            response = self.process(request)
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
        
        XConfig.App = self
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
        
    def run(self):
        run_simple('0.0.0.0', 5000, self.runApp, use_reloader=True, use_debugger=True)    
        
    def runDebug(self):
        app = DebuggedApplication(self.runApp, evalex=True)
        run_simple('0.0.0.0', 5000, app, use_reloader=True, use_debugger=True)