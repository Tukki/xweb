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

    def as_json(self):
        self.context['type'] = 'json'

    def as_string(self):
        self.context['type'] = 'string'


def as_json(func):
    def _as_json(self, *args, **kwargs):
        self.as_json()

        return func(self, *args, **kwargs)
    return _as_json

def as_string(func):
    def _as_string(self, *args, **kwargs):
        self.as_string()

        return func(self, *args, **kwargs)
    return _as_string