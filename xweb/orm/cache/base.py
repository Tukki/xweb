# coding: utf8
'''
Created on 2012-8-31

@author: lifei
'''

import hashlib
def md5(k):
    return hashlib.md5(k).hexdigest()


class CacheClient:
    
    def __init__(self, name, conf):
        pass
    
    def get(self, key):
        return None
    
    def getList(self, key):
        return {}
    
    def set(self, key, value):
        pass
    
    def delete(self, key):
        pass
    
    def updateEntityStatus(self, entity):
        entity._is_new = False
        entity._load_from_cache = True
        entity._cache = self.name
        
        return entity
    

class CacheManager:
    '''
    采用LasyLoad的方式加载DB链接
    '''
    
    def __init__(self, conf):
        
        self.conf = conf
        self.caches = {}
        
    def get(self, name):
        if not self.conf:
            return None
        
        if not self.conf.has_key(name):
            return self.get('default')
        
        if not self.caches.has_key(name):    
            self.caches[name] = CacheClient(name, self.conf.get(name))
            
        return self.caches.get(name)
    
    def close(self):
        for k in self.caches:
            cache = self.caches.get(k)
            cache.close()

