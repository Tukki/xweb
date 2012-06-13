# coding:utf8
'''
Created on 2012-6-3

@author: lifei
'''

import threading
from config import XConfig
from orm.cache import CacheManager
from db import ConnectionManager
from orm.idgenerator import IdGenerator


class EntityStatusError(Exception):
    pass

class UnitOfWork:
    '''
    工作单元
    由于数据库连接线程安全的限制，工作单元只提供thread local的访问实例，不提供进程级实例
    '''
    
    def __init__(self):
        self.connection_manager = ConnectionManager(XConfig.config.get('db'))
        self.cache_manager = CacheManager(XConfig.config.get('cache'))
        self.entity_list = {}
        self.disable_cache = False
        self.disable_preload = False
        
        connection = self.connection_manager.get(XConfig.get('idgenerator', {}).get('connection'))
        self.idgenerator = IdGenerator(connection, XConfig.get('idgenerator', {}).get('count') or 5)
    
    def register(self, entity):
        
        cls_name = entity.__class__.__name__
        
        if self.entity_list.get(cls_name) is None:
            self.entity_list[cls_name] = {}
            
        self.entity_list[cls_name][entity.id] = entity
        
    def commit(self):
        
        deletes = []
        updates = []
        news = []
        connections = set()
        
        for entity_class_name in self.entity_list:
            entity_dict = self.entity_list.get(entity_class_name)
            
            for id in entity_dict:
                entity = entity_dict.get(id)
                
                if entity.isDelete():
                    deletes.append(entity)
                elif entity.isNew():
                    news.append(entity)
                elif entity.isDirty():
                    updates.append(entity)
                else:
                    continue
                    
                connections.add(entity._connection)
                
        for name in connections:
            connection = self.connection_manager.get(name)
            if name == connection.name:
                connection.connect().begin()
                
        try:
            for entitys in [deletes, updates, news]:
                for entity in entitys:
                    self.sync(entity)
                    
            for name in connections:
                connection = self.connection_manager.get(name)
                if name == connection.name:
                    connection.connect().commit()
                    
        except:
            for name in connections:
                connection = self.connection_manager.get(name)
                if name == connection.name:
                    connection.connect().rollback()
        finally:
            self.entity_list.clear()
                    
        
    def load(self, cls, id): #@ReservedAssignment
        cls_name = cls.__name__
        if self.entity_list.get(cls_name) is None:
            return None
        
        return self.entity_list.get(cls_name).get(id)
    
    def getMulti(self, cls, ids, **kwargs):
        
        db_conn = cls.connection(**kwargs)
        connection = self.connection_manager.get(db_conn)
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

        if not entitys:
            return []
        
        first_entity = entitys[0]
        first_entity.setProps('list_ids', ids)
        first_entity.setProps('list_first', first_entity.id)
        for entity in entitys:
            self.register(entity)
            entity.setProps('list_first', first_entity.id)
            
        return [self.load(cls, id) for id in ids]
    
    def getMultiByCond(self, cls, condition=None, args=[], **kwargs):
        
        db_conn = cls.connection(**kwargs)
        connection = self.connection_manager.get(db_conn)
        ids = connection.queryIds(cls, condition, args)
        
        return self.getMulti(cls, ids, **kwargs)
    
    
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
    
    def getForeignEntity(self, entity, key):
        
        fkey, fcls, fid = entity.getForeignKey(key)
        
        if not fid:
            return None
        
        if self.disable_preload:
            return self.get(fcls, fid)
        
        first_id = entity.getProps('list_first', None)
        if  not first_id:
            return self.get(fcls, fid)

        model = self.load(cls, fid)
        
        if model:
            return model
        
        if first_id == fid:
            list_ids = entity.getProps('list_ids', [])
        else:
            model = self.load(cls, first_id)
            if not model:
                return self.get(cls, fid)
            
            list_ids = model.getPrpos('list_ids', [])
        
        fids = set()
        for list_id in list_ids:
            model = self.load(cls, list_id)
            if not model:
                continue
            fid = getattr(model, fkey)
            fids.add(fid)
            
        if fids:
            self.getMulti(cls, fids)
            return self.load(cls, id)
        
        return self.get(cls, id)
        
    
    def sync(self, entity):
        connection = self.connection_manager.get(entity._connection)
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

        raise EntityStatusError()
        
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