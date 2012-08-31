'''
Logging for XWeb

@author: lifei
'''


import logging
import threading
import time

class Logger(threading.local):
    
    def update(self, flag=None):
        if flag:
            self.flag = flag
        else:
            self.flag = ("R%d" % ( int(time.time() * 100) % 10e7 ) )
        
    def getFlag(self):
        if not hasattr(self, 'flag') or not self.flag:
            self.flag = str(time.time())
            
        return self.flag
        
    def debug(self, msg, *args):
        logging.debug("%s\t%s" % (self.getFlag(), msg), *args)
        
    def warn(self, msg, *args):
        logging.warn("%s\t%s" % (self.getFlag(), msg), *args)
        
    def error(self, msg, *args):
        logging.error("%s\t%s" % (self.getFlag(), msg), *args)
        
    def info(self, msg, *args):
        logging.info("%s\t%s" % (self.getFlag(), msg), *args)
        
    def exception(self, msg, *args):
        logging.exception("%s\t%s" % (self.getFlag(), msg), *args)

Log = Logger()