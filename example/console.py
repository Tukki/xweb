'''
Created on 2012-6-4

@author: lifei
'''
import sys
import datetime
import random
sys.path.insert(0, '..')
from domain import User
from xweb.config import XConfig
from xweb.orm import UnitOfWork

import logging

logger = logging.getLogger()
logger.setLevel(10)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
ch.setLevel(10)
logger.addHandler(ch)

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
    },
          
    'idgenerator': {
        'count': 5
    }
    
}

XConfig.load(config)

unitofwork = UnitOfWork.inst()

user = User.get(1)

users = User.getAll('name is not null')

i = 5
for user in users:
    user.name = i*i

user2 = User(id=int(random.random()*1000), name="xxx", passwd="www", create_time=datetime.datetime(2011, 10, 10, 0, 0), address_id=1)

unitofwork.register(user2)

user = User.createByBiz(name="xxx", passwd="www", create_time=datetime.datetime(2011, 10, 10, 0, 0), address_id=1)

user.name = 'bbbb'

print user.id

unitofwork.commit()
