'''
Created on 2012-6-2

@author: lifei
'''
import sys
sys.path.insert(0, '..')

from xweb.mvc import XApplication
from xweb.config import XConfig
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

www_app = XApplication('controllers')

if __name__ == '__main__':
    www_app.runDebug()
