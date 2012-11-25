# coding:utf8
'''
Created on 2012-6-3

@author: lifei
@since: 1.0
'''

import threading
from xweb.util import logging

from cache import CacheManager
from idgenerator import IdGenerator

from xweb.config import XConfig
from xweb.orm.field import QueryCriteria


class EntityStatusError(Exception):
    pass

class ModifyBasedCacheError(Exception):
    pass

class DBError(Exception):
    pass

class UnitOfWork(object):
    '''
    工作单元
    
    @note: 由于数据库连接线程安全的限制，工作单元只提供thread local的访问实例，不提供进程级实例
    '''
    
    def __init__(self):
        from db import ConnectionManager
        self.connection_manager = ConnectionManager(XConfig.get('db'))
        self.cache_manager = CacheManager(XConfig.get('cache'))
        self.entity_list = {}
        self.use_cache = False
        self.use_preload = True
        self.use_validator = False
        self.bad_entitys = []
        
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
        
        for entity_class_name in self.entity_list.keys():
            entity_dict = self.entity_list.get(entity_class_name)
            for entity_id in entity_dict.keys():
                entity = entity_dict.get(entity_id)
                if entity.isDelete():
                    entity.onDelete()
                elif entity.isNew():
                    entity.onNew()
                elif entity.isDirty():
                    entity.onUpdate()
                else:
                    continue
                
        self.bad_entitys = []
        for entity_class_name in self.entity_list.keys():
            entity_dict = self.entity_list.get(entity_class_name)
            for entity_id in entity_dict.keys():
                entity = entity_dict.get(entity_id)
                if entity.isDelete():
                    deletes.append(entity)
                elif entity.isNew():
                    news.append(entity)
                elif entity.isDirty():
                    updates.append(entity)
                else:
                    continue
                
                if entity.isLoadedFromCache():
                    raise ModifyBasedCacheError("%s(%s) is loaded from cache, so can't be modified!!"%(
                        entity.__class__.__name__, entity.id))
                
                if self.use_validator and not entity.doValidate():
                    self.bad_entitys.append(entity)
                    
                db_names.add(entity._db)
                
        if self.use_validator and self.bad_entitys:
            return False
                
        for name in db_names:
            connection = self.connection_manager.get(name)
            if connection and name == connection.name:
                connection.begin()
                
        try:
            for entitys in [deletes, updates, news]:
                for entity in entitys:
                    self.sync(entity)
                    
            for name in db_names:
                connection = self.connection_manager.get(name)
                if name == connection.name:
                    connection.commit()
            
            for entity in deletes:
                try:
                    cache = self.cache_manager.get(entity._cache)
                    if not cache:
                        continue
                    
                    cache_key = self.makeKey(entity.__class__, entity.id)
                    cache.delete(cache_key)
                except:
                    logging.exception("delete cache fail")
                
            for entitys in [updates, news]:
                for entity in entitys:
                    try:
                        cache = self.cache_manager.get(entity._cache)
                        if not cache:
                            continue
                        cache_key = self.makeKey(entity.__class__, entity.id)
                        cache.set(cache_key, entity.getCacheDict())
                    except:
                        logging.exception("set cache fail")
                    
            return True
        except:
            logging.exception("[XWEB] COMMIT FAILED, ROLLBACK")
            for name in db_names:
                connection = self.connection_manager.get(name)
                if name == connection.name:
                    connection.rollback()
            return False
        finally:
            self.entity_list.clear()
                    
        
    def getEntityInMemory(self, cls, entity_id):
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
            
            cache_name = cls._cache_name
            cache = self.cache_manager.get(cache_name)
            if not cache:
                raise ValueError('CACHE DOES NOT EXSITS WHEN USE_CACHE IS TRUE')
            
            entitys = cache.getList(keys)
            
            entity_id_and_keys = zip(not_found_ids, keys)
            for entity_id, key in entity_id_and_keys:
                cache_dict = entitys.get(key)
                if cache_dict:
                    entity = cls(**cache_dict)
                    entity._is_new = False
                    entity._is_delete = False
                    entity._is_dirty = False
                    entity._load_from_cache = True
                    entity._db = 'default'
                    entity._cache = cache_name
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
    
    def getListByCond(self, criteria, **kwargs):
        
        if not isinstance(criteria, QueryCriteria):
            return []
        
        cls = criteria.entity_cls
        
        db_conn = cls.dbName(**kwargs)
        connection = self.connection_manager.get(db_conn)
        entity_ids = connection.fetchEntityIds(criteria)
        
        return self.getList(cls, entity_ids, **kwargs)
    
    
    def fetchRowsByCond(self, cr, **kwargs):
        
        cls = cr.entity_cls
        db_conn = cls.dbName(**kwargs)
        connection = self.connection_manager.get(db_conn)
        return connection.fetchRowsByCond(cr)
    
    
    def fetchRowByCond(self, cr, **kwargs):
        
        cls = cr.entity_cls
        db_conn = cls.dbName(**kwargs)
        connection = self.connection_manager.get(db_conn)
        return connection.fetchRowByCond(cr)
        
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
                cache_name = cls._cache_name
                cache = self.cache_manager.get(cache_name)
                if cache:
                    cache.set(key, entity.getCacheDict())
                
            results.append(entity)
                
        return results
    
    
    def get(self, cls, entity_id, **kwargs): #@ReservedAssignment
        
        entity = self.getEntityInMemory(cls, entity_id)
        if entity:
            return entity
        
        key = self.makeKey(cls, entity_id)
        cache_name = cls._cache_name
        cache = self.cache_manager.get(cache_name)
        if self.use_cache:
            
            cache_dict = cache.get(key)
            if cache_dict:
                entity = cls(**cache_dict)
                entity._is_new = False
                entity._is_delete = False
                entity._is_dirty = False
                entity._load_from_cache = True
                entity._db = 'default'
                entity._cache = cache_name
                self.register(entity)
                logging.debug("LOAD ENTITY %s FROM CACHE: %s"%(entity, cache_name))
                return entity
        
        db_conn = cls.dbName(entity_id=entity_id, **kwargs)
        connection = self.connection_manager.get(db_conn)
        entity = connection.getEntity(cls, entity_id)
        
        if entity is None:
            return None
        
        self.register(entity)
        
        if cache:
            cache.set(key, entity.getCacheDict())
            logging.debug("LOAD ENTITY %s FROM DB: %s"%(entity, db_conn))
        
        return entity
        
    
    def sync(self, entity):
        connection = self.connection_manager.get(entity._db)
        
        if entity.isNew():
            if connection.insert(entity):
                entity._is_dirty = False
                entity._is_new = False
                entity.is_delete = False
                return  True
        elif entity.isDelete():
            if connection.delete(entity):
                entity._is_dirty = False
                entity._is_new = False
                entity.is_delete = True
                return  True
        elif entity.isDirty():
            if connection.update(entity):
                entity._is_dirty = False
                entity._is_new = False
                entity.is_delete = False
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
    def reset(cls, force=False):
        thread = threading.currentThread()
        
        if hasattr(thread, 'unitofwork') and thread.unitofwork:
            if not force:
                unitofwork = thread.unitofwork
                unitofwork.entity_list = {}
                unitofwork.bad_entitys = {}
                unitofwork.use_cache = True
                unitofwork.use_preload = False
            else:
                del thread.unitofwork
