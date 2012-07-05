from xweb.mvc.controller import XController, AsString, AsJSON


class DefaultController(XController):

    @AsJSON
    def doIndex(self):
        from domain import User
        users = User.getAll('name is not null')
        
        i = 5
        for user in users:
            print user.address
        
        self.json(users)
