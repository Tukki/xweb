'''
Created on 2012-6-2

@author: lifei
'''
from mvc import XApp
from config import XConfig
import rewrite

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
    'rewrite_rules': rewrite.rewrite_rules
}

XConfig.load(config)

if __name__ == '__main__':
    XApp().runDebug()