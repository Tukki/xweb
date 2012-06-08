from mvc.controller import XController, as_string
from domain import User

class DefaultController(XController):

    @as_string
    def action_index(self):
        user = User.get(1)
        self.echo(user.name)
        self.echo(user.address.name)
