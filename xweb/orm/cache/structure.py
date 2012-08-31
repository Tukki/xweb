# coding: utf8
'''

@author: lifei
'''
from base import md5
from xweb.orm.unitofwork import UnitOfWork
from xweb.util import logging
import bisect

class BaseCache(object):
    
    key_tmpl = ''
    timeout = -1
    
    def __init__(self, cache_client, data=[], cache_key=None, **kwargs):
        self.cache_client = cache_client
        self.data = data
        
        if cache_key:
            self.cache_key = cache_key
        else:
            self.cache_key = self.__class__.makeKey(**kwargs)
            
        self.kwargs = kwargs
        
    
    def update(self):
        try:
            self.cache_client.set(self.cache_key, self.data)
        except:
            logging.exception("vector cache update failed")
            
    
    @classmethod
    def makeKey(cls, **kwargs):
        return md5(cls.key_tmpl % kwargs)
    
    @classmethod
    def get(cls, use_cache=True, cache_only=False, **kwargs):
        
        cache_key = cls.makeKey(**kwargs)
        cache_client = cls.getClient(**kwargs)
        
        retval = None
        if (cls.canUseCache(use_cache)) or cache_only:
            data = cache_client.get(cache_key)
            if data:
                retval = cls(cache_key=cache_key, cache_client=cache_client, data=data, **kwargs)
            
        if cache_only:
            return retval
            
        if retval is None:
            data = cls._get(**kwargs)
            if data:
                retval = cls(cache_key=cache_key, cache_client=cache_client, data=data, **kwargs)
                retval.update()
        
        return retval
    
    @classmethod
    def _get(cls, **kwargs):
        return cls(**kwargs)
    
    @classmethod
    def cacheName(cls, **kwargs):
        return 'default'
    
    @classmethod
    def getClient(cls, **kwargs):
        cache_name = cls.cacheName(**kwargs)
        return UnitOfWork.inst().cache_manager.get(cache_name)
    
    @classmethod
    def canUseCache(cls, use_cache):
        return UnitOfWork.inst().use_cache and use_cache
    
    
class VectorCache(BaseCache):
    
    def __init__(self, cache_client, data=[], cache_key=None, **kwargs):
        BaseCache.__init__(self, cache_client, data, cache_key, **kwargs)
        
        self.keys = [self.key(r) for r in self.data]
    
    def push(self, item):
        key = self.key(item)
        pos = bisect.bisect(self.keys, key)
        self.keys.insert(pos, key)
        self.data.insert(pos, item)
        
        
    def pushList(self, items):
        for item in items:
            self.push(item)
            
    def key(self, r):
        return r

class StatsCache(BaseCache):
    
    pass