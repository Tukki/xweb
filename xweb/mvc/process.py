'''

@author: lifei
'''

import sys
from controller import XController
import inspect
from jinja2.environment import Environment
from jinja2.loaders import FileSystemLoader
from werkzeug.exceptions import NotFound, HTTPException #@UnresolvedImport
import logging
from web import XRequest, XResponse
from werkzeug.wrappers import BaseResponse
from werkzeug.utils import redirect
import json

class CommitFailedError(Exception):
    pass

class XProcess:

    def __init__(self, app, environ, start_response):
        self.environ = environ
        self.app = app
        self.start_response = start_response

    def __rewrite(self):
        
        for rule in self.app.rewrite_rules:
            path_info = self.environ.get('PATH_INFO', '/')
            q = rule.parseUrl(path_info)
            if q is not None:
                if self.environ['QUERY_STRING']:
                    self.environ['QUERY_STRING'] += '&'+q
                else:
                    self.environ['QUERY_STRING'] = q
                    
                break
    
        self.request = XRequest(self.environ, populate_request=False)
        
        return True
    
    def __process(self):
        
        controller  = self.request.get('c')
        action      = self.request.get('a')

        if controller and action:
            controller = controller.lower()
            action = action.lower()
            controller_module_path = 'controllers.%s'%controller
            if controller == 'default':
                controller_module_path = 'controllers'
            controller_module = sys.modules.get(controller_module_path)
            try:
                if not controller_module:
                    controller_module = __import__(controller_module_path)

                controller_class_name = controller.title().replace('_', '') + 'Controller'
                if not hasattr(controller_module, controller_class_name):
                    return NotFound()
                    
                controller_class = getattr(controller_module, controller_class_name)

                controller_instance = controller_class(self.request)

                if isinstance(controller_instance, XController):
                    action_method = getattr(controller_instance, 'do%s'%action.title())
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
                                kwargs[func_arg] = self.request.args.get(func_args)
                    
                    unitofwork = controller_instance.unitofwork
                    try:
                        controller_instance.before()       
                        action_method(**kwargs)
                        controller_instance.after()
                        unitofwork.commit()
                        context = controller_instance.context

                        if context['code'] == 200:
                            if context['type'] == 'json':
                                return XResponse(context['json'], mimetype='application/json')
                            elif context['type'] == 'string':
                                return XResponse(context['string'], mimetype='text/html')
                            else:
                                template_path = "templates/%s"%controller
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
                        response = BaseResponse(
                            str(ex), 500, mimetype='text/html')
                        return response
                    finally:
                        unitofwork.reset()
                    
            except ImportError, AttributeError:
                logging.exception("Can't find the method to process")
                return NotFound()
                
            except Exception as ex:
                logging.exception(ex)
                return XResponse(str(ex), mimetype='text/html')
        
        return NotFound()

    def run(self):
        response = None
        try:
            if self.__rewrite():
                response = self.__process()
        except HTTPException, ex:
            response = ex
        
        if response:
            return response(self.environ, self.start_response)