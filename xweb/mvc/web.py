'''

@date 2012-6-3
@author: lifei
'''
from werkzeug import Request, Response

class XRequest(Request):
    
    def __init__(self, *args, **kwargs):
        self.context = {}
        Request.__init__(self, *args, **kwargs) #@UndefinedVariable
    
    def get(self, key):
        for _list in [self.context, self.cookies, self.args]:
            if _list and _list.has_key(key):
                return _list.get(key)
            
        return None

class XResponse(Response):
    pass
