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
        logging.debug("%s cost %.2f ms", self.profiler_name, 1000 * (end_time - self.begin_time))
