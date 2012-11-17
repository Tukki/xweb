'''

@date 2012-6-3
@author: lifei
'''
from werkzeug import Request, Response
from werkzeug.utils import cached_property
from werkzeug.contrib.securecookie import SecureCookie
from xweb.config import XConfig


class XRequest(Request):
    
    def __init__(self, *args, **kwargs):
        self.context = {}
        Request.__init__(self, *args, **kwargs)
        # self.stream, self.form, self.files = parse_form_data(self.environ)
        
        self.context.update(self.args.to_dict())
        self.context.update(self.form.to_dict())
        self.context.update(self.cookies)
        self.context['request'] = self
    
    def get(self, key, value=None):
        return self.context.get(key, value)
    
    def getInt(self, key, value=0):
        
        try:
            return int(self.context.get(key))
        except:
            return value
    
    def getFloat(self, key, value=0):
        
        try:
            return float(self.context.get(key))
        except:
            return value
    
    def getLong(self, key, value=0):
        
        try:
            return long(self.context.get(key))
        except:
            return value
    
    @cached_property
    def secure_cookies(self):
        return SecureCookie.load_cookie(self, secret_key=XConfig.get('COOKIE_SECRET_KEY') or 'xweb')
    
class XResponse(Response):
    pass
