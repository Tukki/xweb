from xweb.mvc.controller import *
from xweb.config import XConfig
from werkzeug.exceptions import NotFound, HTTPException #@UnresolvedImport
from xweb.mvc.web import XResponse


class DefaultController(XController):

    @settings(mimetype='xml')
    def doIndex(self):

        self.echo("hehe")
        import time
        self.context['user'] = time.time()
        
        for i in range(1000):
            self.secure_cookies[i] = i*i 

        self.context['link'] = self.createUrl('default/long', short_id=110000L)
       
    def doHelp(self):
        self.echo("hello world")
        
        
    @settings(mimetype='text')
    def doShort(self):
        self.echo(self.createUrl('default/short', short_id=110000L))
        
    @settings(status_code=500)
    def handleException(self, **kwargs):
        ex = kwargs.get('ex')
        assert isinstance(ex, Exception)
        self.response.data = str(ex)
        
        if self.app.use_debuger:
            raise
