# coding: utf8
'''
@author: lifei
'''


from xweb.orm import UnitOfWork
from xweb.mvc.web import XResponse

class XController(object):

    def __init__(self, request, application):
        self.unitofwork = UnitOfWork.inst()
        self.request = request
        self.response = XResponse()
        self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
        self.app = application
        
        self.context.update({
            'code':200,
            'type':'html',
            'string': '',
            'json':None,
        })
        
        self.content_type = 'html'
        self.charset = 'utf-8'
        
        # 识别这个请求是否是只读的
        self.read_only = False
        
        # for short
        self.createUrl = self.app.createUrl
        self.headers = self.response.headers
        self.setCookies = self.response.set_cookie
        self.context = self.request.context
        
    def beforeAction(self):
        pass
    
    def afterAction(self):
        pass
        
    def echo(self, string):
        self.context['string'] += str(string)
        
    def json(self, obj):
        self.context['json'] = obj

    def asJSON(self):
        self.response.headers['Content-Type'] = 'application/json; charset=%s' % self.charset
        self.context_type = 'json'

    def asString(self):
        self.response.headers['Content-Type'] = 'text/plain; charset=%s' % self.charset
        self.context_type = 'string'

    def setCode(self, code, desc=None):
        self.response.status_code = code
        self.context['description'] = desc
        
    def redirect(self, url):
        self.response.status_code = 302
        self.response.headers['Location'] = url
        
    def redirect301(self, url):
        self.response.status_code = 301
        self.response.headers['Location'] = url
        
    def __getattribute__(self, key, *args, **kwargs):
        
        try:
            return object.__getattribute__(self, key, *args, **kwargs)
        except:
            
            for k in ['request', 'response']:
                if hasattr(object.__getattribute__(self, k), key):
                    return getattr(object.__getattribute__(self, k), key, *args, **kwargs)
            
            return None


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