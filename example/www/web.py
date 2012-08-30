'''
Created on 2012-6-2

@author: lifei
'''
import sys
import os

script_path = os.path.dirname(__file__)

if script_path and not script_path.endswith('/'):
    script_path += '/'

sys.path.insert(0, '%s../..' % script_path)
sys.path.insert(0, '%s..' % script_path)

from xweb.mvc import XApplication
from xweb.config import XConfig
import rewrite
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
            'db': 'app_video360',
            'charset': 'utf8'
        }
    },
    'cache': {
        'default':'127.0.0.1:2000'
    },
    'rewrite_rules': rewrite.rewrite_rules
}

XConfig.load(config)

www_app = XApplication('www',  '%s..' % script_path)

if __name__ == '__main__':
    www_app.runDebug()
