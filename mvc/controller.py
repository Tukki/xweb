'''
Created on 2012-6-2

@author: lifei
'''
from orm.unitofwork import UnitOfWork


class XController:

    def __init__(self, request):
        UnitOfWork.reset()
        self.unitofwork = UnitOfWork.inst()
        self.request = request
        self.context = {
            'code':200,
            'type':'html',
            'string': ''
            }
        
    def before(self):
        pass
    
    def after(self):
        pass
        
    def echo(self, string):
        self.context['string'] += str(string)
        
    def json(self, obj):
        self.context['json'] = obj

    def asJSON(self):
        self.context['type'] = 'json'

    def asString(self):
        self.context['type'] = 'string'


def AsJSON(func):
    def _AsJSON(self, *args, **kwargs):
        self.asJSON()

        return func(self, *args, **kwargs)
    return _AsJSON

def AsString(func):
    def _AsString(self, *args, **kwargs):
        self.asString()

        return func(self, *args, **kwargs)
    return _AsString