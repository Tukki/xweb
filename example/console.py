'''
Created on 2012-6-4

@author: lifei
'''
import sys
import datetime
sys.path.insert(0, '..')
from domain import User
from config import XConfig
from orm.unitofwork import UnitOfWork

config = {
    'db': {
        'default': {
            'driver':'mysql',   
            'user': 'root',
            'passwd': '',
            'host': '127.0.0.1',
            'db': 'test',
            'charset': 'utf8'
        }
    },
    'cache': {
        'default':'127.0.0.1:2000'
    }
}

XConfig.load(config)

unitofwork = UnitOfWork.inst()

user = unitofwork.get(User, 1)

user.address.name = 10

unitofwork.sync(user.address)

print user.address.__dict__

user2 = User(id=3, name="xxx", passwd="www", create_time=datetime.datetime(2011, 10, 10, 0, 0), address_id=1)

#unitofwork.sync(user2)

print unitofwork.getMulti(User, '')