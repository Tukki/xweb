# coding:utf8
'''
Created on 2012-6-3

@author: lifei
'''

import threading
from config import XConfig
from orm.cache import CacheManager
from db import ConnectionManager


class EntityStatusError(Exception):
    pass

class UnitOfWork:
    '''
    工作单元
    '''
    
    def __init__(self):
        self.connection_manager = ConnectionManager(XConfig.config.get('db'))
        self.cache_manager = CacheManager(XConfig.config.get('cache'))
        self.entity_list = {}
        self.disable_cache = False
    
    def register(self, entity):
        
        cls_name = entity.__class__.__name__
        
        if self.entity_list.get(cls_name) is None:
            self.entity_list[cls_name] = {}
            
        self.entity_list[cls_name][entity.id] = entity
        
    def load(self, cls, id): #@ReservedAssignment
        cls_name = cls.__name__
        if self.entity_list.get(cls_name) is None:
            return None
        
        return self.entity_list.get(cls_name).get(id)
    
    def getMulti(self, cls, condition=None, args=[], **kwargs):
        
        db_conn = cls.connection(**kwargs)
        connection = self.connection_manager.get(db_conn)
        ids = connection.queryIds(cls, condition, args)
        
        query_db_ids = []
        if not self.disable_cache:
            not_found_ids = []
            for id in ids:
                entity = self.load(cls, id)
                if not entity:
                    not_found_ids.append(id)
                    
            keys = [self.makeKey(cls, id) for id in not_found_ids]
            
            cache_name = cls.cache(**kwargs)
            cache = self.cache_manager.get(cache_name)
            
            entitys = cache.getMulti(keys)
            id_and_keys = zip(not_found_ids, keys)
            for id, key in id_and_keys:
                entity = entitys.get(key)
                if entity:
                    self.register(entity)
                else:
                    query_db_ids.append(id)
        else:
            query_db_ids = ids
        
        entitys = connection.queryAll(cls, query_db_ids)
        
        for entity in entitys:
            self.register(entity)
            
        return [self.load(cls, id) for id in ids]
    
    def get(self, cls, id, **kwargs): #@ReservedAssignment
        
        key = self.makeKey(cls, id)
        cache_name = cls.cache(id=id, **kwargs)
        cache = self.cache_manager.get(cache_name)

        if not self.disable_cache:
            entity = self.load(cls, id)
            if entity:
                return entity
            
            entity = cache.get(key)
            if entity:
                return entity
        
        db_conn = cls.connection(id=id, **kwargs)
        connection = self.connection_manager.get(db_conn)
        entity = connection.query(cls, id)
        
        if entity is None:
            return None
        
        self.register(entity)
        cache.set(key, entity)
        
        return entity
    
    def sync(self, entity):
        connection = self.connection_manager.get(entity._connection)
        if entity.isNew():
            return connection.insert(entity)
        elif entity.isDelete():
            return connection.delete(entity)
        elif entity.isDirty():
            return connection.update(entity)

        raise EntityStatusError()
        
    def get_multi(self, cls, ids):
        pass
    
    def makeKey(self, cls, id):
        return "%s:%s:%s:%s"%(XConfig.config.get('app_name'),
                              cls.__name__, id, cls._version)
    
    
    
    #==== class method =====
    
    @classmethod
    def inst(cls):
        thread = threading.currentThread()
        
        if not hasattr(thread, 'unitofwork'):
            thread.unitofwork = UnitOfWork()
            
        return thread.unitofwork
    
    @classmethod
    def reset(cls):
        thread = threading.currentThread()
        
        if hasattr(thread, 'unitofwork'):
            del thread.unitofwork