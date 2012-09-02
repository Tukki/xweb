# coding:utf8
'''
Created on 2012-6-3

@author: lifei
@since: 1.0
'''

import threading
import logging

from cache import CacheManager
from idgenerator import IdGenerator

from xweb.config import XConfig


class EntityStatusError(Exception):
    pass

class ModifyBasedCacheError(Exception):
    pass

class UnitOfWork(object):
    '''
    工作单元
    
    NOTE: 由于数据库连接线程安全的限制，工作单元只提供thread local的访问实例，不提供进程级实例
    '''
    
    def __init__(self):
        from db import ConnectionManager
        self.connection_manager = ConnectionManager(XConfig.get('db'))
        self.cache_manager = CacheManager(XConfig.get('cache'))
        self.entity_list = {}
        self.use_cache = True
        self.use_preload = True
        
    def idgenerator(self):
        
        if not hasattr(self, '_idgenerator') or not self._idgenerator:
            connection = self.connection_manager.get(XConfig.get('idgenerator.db'))
            self._idgenerator = IdGenerator(connection, XConfig.get('idgenerator.count') or 5)
            
        return self._idgenerator
        
    
    def register(self, entity):
        '''注册实体到工作单元
        '''
        
        cls_name = entity.__class__.__name__
        
        if self.entity_list.get(cls_name) is None:
            self.entity_list[cls_name] = {}
            
        self.entity_list[cls_name][str(entity.getId())] = entity
        entity._unitofwork = self
        
    def commit(self):
        '''
        '''
        
        deletes = []
        updates = []
        news = []
        db_names = set()
        
        for entity_class_name in self.entity_list:
            entity_dict = self.entity_list.get(entity_class_name)
            
            for entity_id in entity_dict:
                entity = entity_dict.get(entity_id)
                
                if entity.isLoadedFromCache():
                    raise ModifyBasedCacheError("%s(%s) is loaded from cache, so can't be modified!!"%(
                        entity.__class__.__name__, entity.id))
                
                if entity.isDelete():
                    deletes.append(entity)
                elif entity.isNew():
                    news.append(entity)
                elif entity.isDirty():
                    updates.append(entity)
                else:
                    continue
                    
                db_names.add(entity._db)
                
        for name in db_names:
            connection = self.connection_manager.get(name)
            if name == connection.name:
                connection.connect().begin()
                
        try:
            for entitys in [deletes, updates, news]:
                for entity in entitys:
                    self.sync(entity)
                    
            for name in db_names:
                connection = self.connection_manager.get(name)
                if name == connection.name:
                    connection.connect().commit()
            
            for entity in deletes:
                try:
                    cache = self.cache_manager.get(entity._cache)
                    cache_key = self.makeKey(entity.__class__, entity.id)
                    cache.delete(cache_key)
                except:
                    pass
                
            for entitys in [updates, news]:
                for entity in entitys:
                    try:
                        cache = self.cache_manager.get(entity._cache)
                        cache_key = self.makeKey(entity.__class__, entity.id)
                        cache.set(cache_key, entity)
                    except:
                        pass
                    
            return True
        except:
            logging.exception("error in commit")
            for name in db_names:
                connection = self.connection_manager.get(name)
                if name == connection.name:
                    connection.connect().rollback()
            return False
        finally:
            self.entity_list.clear()
                    
        
    def getEntityInMemory(self, cls, entity_id): #@ReservedAssignment
        cls_name = cls.__name__
        if self.entity_list.get(cls_name) is None:
            return None
        
        return self.entity_list.get(cls_name).get(str(entity_id))
    
    def getList(self, cls, entity_ids, **kwargs):
        
        db_conn = cls.dbName(**kwargs)
        connection = self.connection_manager.get(db_conn)
        query_db_ids = []
        if self.use_cache:
            not_found_ids = []
            for entity_id in entity_ids:
                entity = self.getEntityInMemory(cls, entity_id)
                if not entity:
                    not_found_ids.append(entity_id)
                    
            keys = [self.makeKey(cls, entity_id) for entity_id in not_found_ids]
            
            cache_name = cls.cacheName(**kwargs)
            cache = self.cache_manager.get(cache_name)
            
            entitys = cache.getList(keys)
            entity_id_and_keys = zip(not_found_ids, keys)
            for entity_id, key in entity_id_and_keys:
                entity = entitys.get(key)
                if entity:
                    self.register(entity)
                else:
                    query_db_ids.append(entity_id)
        else:
            query_db_ids = entity_ids
        
        entitys = connection.getEntityList(cls, query_db_ids)

        if not entitys:
            return []
        
        first_entity = entitys[0]
        first_entity.setProps('entity_ids_in_query', entity_ids)
        for entity in entitys:
            self.register(entity)
            entity.setProps('first_entity_in_query', first_entity.id)
            
        return [self.getEntityInMemory(cls, entity_id) for entity_id in entity_ids if self.getEntityInMemory(cls, entity_id)]
    
    def getListByCond(self, cls, condition=None, args=[], **kwargs):
        
        db_conn = cls.dbName(**kwargs)
        connection = self.connection_manager.get(db_conn)
        entity_ids = connection.fetchEntityIds(cls, condition, args)
        
        return self.getList(cls, entity_ids, **kwargs)
    
    def getListByCond2(self, cls, condition=None, args=[], **kwargs):
        
        db_conn = cls.dbName(**kwargs)
        connection = self.connection_manager.get(db_conn)
        rows = connection.queryRowsByCond(cls, condition, args)
        
        results = []
        
        for row in rows:
            
            data = {}
            
            for k,v in zip(cls.allKeys(), row):
                data[k] = v
                
            entity_id = tuple([data.get(k) for k in cls.primaryKey()])
            
            entity = self.getEntityInMemory(cls, entity_id)
            
            if not entity:
                entity = connection.createEntity(cls, row)
                self.register(entity)
                key = self.makeKey(cls, entity_id)
                cache_name = cls.cacheName(key=key, entity_id=entity_id, **kwargs)
                cache = self.cache_manager.get(cache_name)
                cache.set(key, entity)
                
            results.append(entity)
                
        return results
    
    
    def get(self, cls, entity_id, **kwargs): #@ReservedAssignment
        
        key = self.makeKey(cls, entity_id)
        cache_name = cls.cacheName(entity_id=entity_id, **kwargs)
        cache = self.cache_manager.get(cache_name)

        if self.use_cache:
            entity = self.getEntityInMemory(cls, entity_id)
            if entity:
                return entity
            
            entity = cache.get(key)
            if entity:
                self.register(entity)
                logging.debug("load entity %s from cache: %s"%(entity, cache_name))
                return entity
        
        db_conn = cls.dbName(entity_id=entity_id, **kwargs)
        connection = self.connection_manager.get(db_conn)
        entity = connection.getEntity(cls, entity_id)
        
        if entity is None:
            return None
        
        self.register(entity)
        cache.set(key, entity)
        logging.debug("load entity %s from db: %s"%(entity, db_conn))
        
        return entity
        
    
    def sync(self, entity):
        connection = self.connection_manager.get(entity._db)
        
        if entity.isNew():
            if connection.insert(entity):
                entity._is_dirty = False
                entity._is_new = False
                entity.is_delete = False
                entity.onNew()
                return  True
        elif entity.isDelete():
            if connection.delete(entity):
                entity._is_dirty = False
                entity._is_new = False
                entity.is_delete = True
                entity.onDelete()
                return  True
        elif entity.isDirty():
            if connection.update(entity):
                entity._is_dirty = False
                entity._is_new = False
                entity.is_delete = False
                entity.onUpdate()
                return True
        else:
            raise EntityStatusError()
        
        return False
        
    def makeKey(self, cls, entity_id):
        return "%s:%s:%s:%s"%(XConfig.get('app_name'),
                              cls.__name__, entity_id, cls._version)
        
    def close(self):
        self.connection_manager.close()
    
    
    # static method
    @classmethod
    def inst(cls):
        thread = threading.currentThread()
        
        if not hasattr(thread, 'unitofwork') or not thread.unitofwork:
            thread.unitofwork = UnitOfWork()
            
        return thread.unitofwork
    
    @classmethod
    def reset(cls):
        thread = threading.currentThread()
        
        if hasattr(thread, 'unitofwork') and thread.unitofwork:
            unitofwork = thread.unitofwork        
            unitofwork.entity_list = {}
            unitofwork.use_cache = True
            unitofwork.use_preload = False
            unitofwork.connection_manager.has_loaded = {}
