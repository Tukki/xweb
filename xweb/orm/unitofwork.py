# coding:utf8
'''
Created on 2012-6-3

@author: lifei
@since: 1.0
'''

import threading
from xweb.config import XConfig
from cache import CacheManager
from db import ConnectionManager
from idgenerator import IdGenerator
import logging


class EntityStatusError(Exception):
    pass

class ModifyBasedCacheError(Exception):
    pass

class UnitOfWork:
    '''
    工作单元
    
    NOTE: 由于数据库连接线程安全的限制，工作单元只提供thread local的访问实例，不提供进程级实例
    '''
    
    def __init__(self):
        self.connection_manager = ConnectionManager(XConfig.get('db'))
        self.cache_manager = CacheManager(XConfig.get('cache'))
        self.entity_list = {}
        self.disable_cache = False
        self.disable_preload = False
        
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
            
        self.entity_list[cls_name][entity.id] = entity
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
            
            for id in entity_dict:
                entity = entity_dict.get(id)
                
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
                    
        
    def getEntityInMem(self, cls, id): #@ReservedAssignment
        cls_name = cls.__name__
        if self.entity_list.get(cls_name) is None:
            return None
        
        return self.entity_list.get(cls_name).get(id)
    
    def getAll(self, cls, ids, **kwargs):
        
        db_conn = cls.dbName(**kwargs)
        connection = self.connection_manager.get(db_conn)
        query_db_ids = []
        if not self.disable_cache:
            not_found_ids = []
            for id in ids:
                entity = self.getEntityInMem(cls, id)
                if not entity:
                    not_found_ids.append(id)
                    
            keys = [self.makeKey(cls, id) for id in not_found_ids]
            
            cache_name = cls.cacheName(**kwargs)
            cache = self.cache_manager.get(cache_name)
            
            entitys = cache.getAll(keys)
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

        if not entitys:
            return []
        
        first_entity = entitys[0]
        first_entity.setProps('list_ids', ids)
        for entity in entitys:
            self.register(entity)
            entity.setProps('list_first', first_entity.id)
            
        return [self.getEntityInMem(cls, id) for id in ids]
    
    def getAllByCond(self, cls, condition=None, args=[], **kwargs):
        
        db_conn = cls.dbName(**kwargs)
        connection = self.connection_manager.get(db_conn)
        ids = connection.queryIds(cls, condition, args)
        
        return self.getAll(cls, ids, **kwargs)
    
    
    def get(self, cls, id, **kwargs): #@ReservedAssignment
        
        key = self.makeKey(cls, id)
        cache_name = cls.cacheName(id=id, **kwargs)
        cache = self.cache_manager.get(cache_name)

        if not self.disable_cache:
            entity = self.getEntityInMem(cls, id)
            if entity:
                return entity
            
            entity = cache.get(key)
            if entity:
                self.register(entity)
                logging.debug("load entity %s from cache: %s"%(entity, cache_name))
                return entity
        
        db_conn = cls.dbName(id=id, **kwargs)
        connection = self.connection_manager.get(db_conn)
        entity = connection.queryOne(cls, id)
        
        if entity is None:
            return None
        
        self.register(entity)
        cache.set(key, entity)
        logging.debug("load entity %s from db: %s"%(entity, db_conn))
        
        return entity
    
    def getBelongsToEntity(self, entity, key):
        
        fkey, cls, fid = entity.getBelongsToInfo(key)
        
        if not fid:
            return None
        
        if self.disable_preload:
            return self.get(cls, fid)
        
        first_id = entity.getProps('list_first', None)
        if  not first_id:
            return self.get(cls, fid)

        model = self.getEntityInMem(cls, fid)
        
        if model:
            return model
        
        if first_id == fid:
            list_ids = entity.getProps('list_ids', [])
        else:
            model = self.getEntityInMem(cls, first_id)
            if not model:
                return self.get(cls, fid)
            
            list_ids = model.getPrpos('list_ids', [])
        
        fids = set()
        for list_id in list_ids:
            model = self.getEntityInMem(cls, list_id)
            if not model:
                continue
            fid = getattr(model, fkey)
            fids.add(fid)
            
        if fids:
            self.getAll(cls, fids)
            logging.debug("preload %s in (%s)"%(cls.modelName(), ",".join(fids)))
            return self.getEntityInMem(cls, fid)
        
        return self.get(cls, fid)
        
    
    def sync(self, entity):
        connection = self.connection_manager.get(entity._db)
        cache = self.cache_manager.get(entity._cache)
        cache_key = self.makeKey(entity.__class__, entity.id)
        
        if entity.isNew():
            if connection.insert(entity):
                entity._is_dirty = False
                entity._is_new = False
                entity.is_delete = False
                entity.onNew()
                cache.set(cache_key, entity)
                return  True
        elif entity.isDelete():
            if connection.delete(entity):
                entity._is_dirty = False
                entity._is_new = False
                entity.is_delete = True
                cache.delete(cache_key)
                entity.onDelete()
                return  True
        elif entity.isDirty():
            if connection.update(entity):
                entity._is_dirty = False
                entity._is_new = False
                entity.is_delete = False
                cache.set(cache_key, entity)
                entity.onUpdate()
                return True
        else:
            raise EntityStatusError()
        
        return False
        
    def makeKey(self, cls, id):
        return "%s:%s:%s:%s"%(XConfig.get('app_name'),
                              cls.__name__, id, cls._version)
        
    def close(self):
        self.connection_manager.close()
    
    
    # static method
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
            unitofwork = thread.unitofwork        
            unitofwork.entity_list = {}
            unitofwork.disable_cache = False
            unitofwork.disable_preload = False