from xweb.mvc.controller import XController, AsString, AsJSON
from xweb.config import XConfig
from werkzeug.exceptions import NotFound, HTTPException #@UnresolvedImport
from xweb.mvc.web import XResponse
from lazr.restfulclient.errors import BadRequest


class DefaultController(XController):

    def doIndex(self):
        self.echo("hehe")
        import time
        self.context['user'] = time.time()
        self.setCode(500, 'HHH')
       
    @AsString 
    def doHelp(self):
        self.echo("hello world")
        
        
    @AsString
    def doShort(self):
        print dir(self.request)
        self.echo(self.request.get('short_id'))
        self.echo(XConfig.App.createUrl('default/long', {'short_id':110000L}))
        
    def handleException(self, **kwargs):
        ex = kwargs.get('ex')
        assert isinstance(ex, Exception)
        self.setCode(500)
        self.response.data = str(ex)
        
        if self.app.use_debuger:
            raise
