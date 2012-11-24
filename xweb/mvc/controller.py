# coding: utf8
'''
@author: lifei
'''


from xweb.orm import UnitOfWork
from xweb.mvc.web import XResponse
import logging

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
        
        self.mimetype = 'html'
        self.charset = self.response.charset
        
        # 识别这个请求是否是只读的
        self.read_only = False
        
        # for short
        self.createUrl      = self.app.createUrl
        self.headers        = self.response.headers
        self.setCookies     = self.response.set_cookie
        self.secure_cookies = self.request.secure_cookies
        self.context        = self.request.context
        self.json           = {}
        self.action         = 'index'
        
        self.context['controller']  = self
        self.context['this']  = self
        self.context['createUrl']  = self.app.createUrl
        
    def getdata(self):
        return self.response.data
    
    def setdata(self, text):
        self.response.data = text
        
    data = property(getdata, setdata, None, "输出的data")
    
    def getstatuscode(self):
        return self.response.status_code
    
    def setstatuscode(self, code):
        self.response.status_code = code
        
    status_code = property(getstatuscode, setstatuscode, 200, 200)
    
    def getmimetype(self):
        return self.content_type
    
    def setmimetype(self, mimetype):
        self.content_type = mimetype
        header = content_type_map.get(mimetype, 'text/html')
        self.response.mimetype = header
    
    mimetype = property(getmimetype, setmimetype, "text/html", "text/html")
    
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
        
    def redirect(self, url):
        self.response.status_code = 302
        self.response.location = url
        
    def redirect301(self, url):
        self.response.status_code = 301
        self.response.location = url

    def end(self, status_code=200, message=None):
        self.read_only = True
        if self.content_type not in ['json', 'text']:
            self.content_type = 'text'
        
        self.status_code = status_code
        if status_code > 400:
            self.context['description'] = message
            
    def afterRender(self):
        UnitOfWork.reset()
