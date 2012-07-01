from mvc.controller import XController, AsString, AsJSON
from domain import User

class DefaultController(XController):

    @AsJSON
    def doIndex(self):
        users = User.getAll('name is not null')
        
        i = 5
        for user in users:
            print user.address
        
        self.json(users)
