'''
@author: lifei
'''


from xweb.orm import UnitOfWork
from xweb.mvc.web import XResponse

class XController:

    def __init__(self, request, app):
        UnitOfWork.reset()
        self.unitofwork = UnitOfWork.inst()
        self.request = request
        self.response = XResponse()
        self.app = app
        self.context = {
            'code':200,
            'type':'html',
            'string': '',
            'json':None,
        }
        
    def before(self):
        pass
    
    def after(self):
        pass
        
    def echo(self, string):
        self.context['string'] += str(string)
        
    def json(self, obj):
        self.context['json'] = obj

    def asJSON(self):
        self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
        self.context['type'] = 'json'

    def asString(self):
        self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
        self.context['type'] = 'string'

    def setCode(self, code, desc=None):
        self.response.status_code = code
        self.context['description'] = desc
        
    def redirect(self, url):
        self.response.status_code = 302
        self.response.headers['Location'] = url


def AsJSON(func):
    def _AsJSON(self, *args, **kwargs):
        self.asJSON()

        return func(self, *args, **kwargs)
    return _AsJSON

def AsString(func):
    def _AsString(self, *args, **kwargs):
        self.asString()

        return func(self, *args, **kwargs)
    return _AsString