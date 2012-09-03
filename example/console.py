'''
Created on 2012-6-4

@author: lifei
'''
import sys
import datetime
import random
sys.path.insert(0, '..')
from xweb.config import XConfig
from xweb.orm import UnitOfWork

import logging

logger = logging.getLogger()
logger.setLevel(10)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
ch.setLevel(10)
logger.addHandler(ch)

