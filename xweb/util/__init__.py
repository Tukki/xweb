from logger import logging
from wsgi import SubDomainDispatcherMiddleware
import time


class BlockProfiler(object):
    '''
    '''

    def __init__(self, profiler_name):
        self.profiler_name = profiler_name

    def __enter__(self):
        self.begin_time = time.time()

    def __exit__(self, _type, value, traceback):
        end_time = time.time()
        logging.debug("%s COST %.2f ms", self.profiler_name, 1000 * (end_time - self.begin_time))
        
        
def block_profiler(func):
    
    def _func(*args, **kwargs):
        begin_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logging.debug("%s.%s COST %.2f ms", 
                      func.__module__, func.__name__, 
                      1000 * (end_time - begin_time))
        
        return result
        
    return _func