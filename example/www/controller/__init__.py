from xweb.mvc.controller import XController, AsString, AsJSON
from xweb.config import XConfig


class DefaultController(XController):

    @AsString
    def doIndex(self):
        from domain import User
        users = User.getAll('name is not null')
        self.echo(users)
       
    @AsString 
    def doHelp(self):
        self.echo("hello world")
        
        
    @AsString
    def doShort(self):
        print dir(self.request)
        self.echo(self.request.get('short_id'))
        self.echo(XConfig.App.createUrl('default/long', {'short_id':110000L}))
