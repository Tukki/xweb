# coding: utf8
'''
@author: lifei
'''


from xweb.orm import UnitOfWork
from xweb.mvc.web import XResponse

content_type_map = {
    'json': 'application/json',
    'text': 'text/plain',
    'text': 'text/plain',
    'xml':  'application/xml',
    'html': 'text/html',
}



class XController(object):

    def __init__(self, request, application):
        self.unitofwork = UnitOfWork.inst()
        self.request = request
        self.response = XResponse()
        self.app = application
        
        self.setContentType('html')
        self.charset = self.response.charset
        
        # 识别这个请求是否是只读的
        self.read_only = False
        
        # for short
        self.createUrl      = self.app.createUrl
        self.headers        = self.response.headers
        self.mimetype       = self.response.mimetype
        self.setCookies     = self.response.set_cookie
        self.secure_cookies = self.request.secure_cookies
        self.context        = self.request.context
        self.json           = {}
        self.action         = 'index'
        
        self.context['controller']  = self
        
    def getdata(self):
        return self.response.data
    
    def setdata(self, text):
        self.response.data = text
        
    data = property(getdata, setdata, None, "输出的data")

    def commit(self):
        return not self.read_only and self.unitofwork.commit()
        
    def beforeAction(self):
        return True
    
    def afterAction(self):
        pass
        
    def echo(self, text, *args, **kwargs):
        
        if kwargs:
            self.data += str(text % kwargs)
        elif args:
            self.data += str(text % args)
        else:
            self.data += str(text)
        
    def setContentType(self, content_type):
        self.content_type = content_type
        header = content_type_map.get(content_type, 'text/plain')
        self.response.mimetype = header

    def setStatusCode(self, code, desc=None):
        self.response.status_code = code
        self.context['description'] = desc
        
    def redirect(self, url):
        self.response.status_code = 302
        self.response.location = url
        
    def redirect301(self, url):
        self.response.status_code = 301
        self.response.location = url

    def end(self):
        self.read_only = True

        if self.content_type not in ['json', 'text']:
            self.content_type = 'text'
            
    def afterRender(self):
        UnitOfWork.reset()


def settings(mimetype=None, charset=None, read_only=None, use_cache=None, status_code=None):
    def _func(func):
        def __func(self, *args, **kwargs):
            if mimetype is not None:
                self.setContentType(mimetype)

            if charset is not None:
                self.response.charset = charset

            if read_only is not None:
                self.read_only = read_only

            if use_cache is not None:
                self.use_cache = use_cache

            if status_code is not None:
                self.response.status_code = status_code

            return func(self, *args, **kwargs)
        return __func
    return _func
