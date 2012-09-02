'''
Logging for XWeb

@author: lifei
'''

import threading
import time

class ThreadLocalLogger(threading.local):
    
    def __init__(self):
        import logging
        self.flag = ("R%d" % ( int(time.time() * 100) % 10e7 ) )
        self.logging = logging
    
    def update(self, flag=None):
        if flag:
            self.flag = flag
        else:
            self.flag = ("R%d" % ( int(time.time() * 100) % 10e7 ) )
        
    def getFlag(self):
        if not hasattr(self, 'flag') or not self.flag:
            self.flag = ("R%d" % ( int(time.time() * 100) % 10e7 ) )
            
        return self.flag
    
    def debug(self, msg, *args):
        self.logging.debug("%s\t%s" % (self.getFlag(), msg), *args)
        
    def warn(self, msg, *args):
        self.logging.warn("%s\t%s" % (self.getFlag(), msg), *args)
        
    def error(self, msg, *args):
        self.logging.error("%s\t%s" % (self.getFlag(), msg), *args)
        
    def info(self, msg, *args):
        self.logging.info("%s\t%s" % (self.getFlag(), msg), *args)
        
    def exception(self, msg, *args):
        self.logging.exception("%s\t%s" % (self.getFlag(), msg), *args)

logging = ThreadLocalLogger()