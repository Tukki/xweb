#coding:utf8
'''
Created on 2012-6-3

@author: lifei
'''
#coding:utf8
import hashlib
import time

def md5(k):
    return hashlib.md5(k).hexdigest()


class CacheClient:
    
    def __init__(self, name, conf):
        pass
    
    def get(self, key):
        return None
    
    def getAll(self, key):
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
        if not self.conf.has_key(name):
            return self.get('default')
        
        if not self.caches.has_key(name):    
            self.caches[name] = CacheClient(name, self.conf.get(name))
            
        return self.caches.get(name)
    
    def close(self):
        for k in self.caches:
            cache = self.caches.get(k)
            cache.close()
            
            
            
#
#class ModelCache:
#    """
#    """
#    
#    def __init__(self):
#        self.mc = mc.model_cache
#        #self.found_item_dict = {}
#
#    def get(self, model_cls, model_id, cache=True):
#        """
#        由id拿到model
#        @param model_cls: 类
#        @param model_id: 主键
#        @return: model类
#        """
#        
#        cache = cache and application.get_conf('cache')
#        
#        if not model_cls or not model_id:
#            return None
#        
#        cache_key = self.mc.makeKey(model=str(model_cls), model_id=model_id)
#
#        v = None
#        if cache:
#            v = self._get_from_mc(cache_key)
#            
#        if not v:
#            v = self._get_from_db(model_cls, model_id)
#            self._write_to_mc(cache_key, v)
#
#        return v
#
#    def get_multi(self, model_cls, model_id_list, cache=True):
#        """
#        由id列表拿到model列表，按照顺序排序，只能取指定model_cls
#        @param model_cls: 类
#        @param model_id_list: 主键的列表
#        @return: model类
#        """
#        if not model_id_list or len(model_id_list) == 0:
#            return []
#
#        cache = cache and application.get_conf('cache')
#        
#        all_cache_key_list = []
#        not_found_dict = {}
#        all_found_item_dict = {}
#
#        for model_id in model_id_list:
#            cache_key = self.mc.makeKey(model=str(model_cls), model_id=model_id)
#            all_cache_key_list.append(cache_key)
#            
#            if not cache:
#                not_found_dict[model_id] = cache_key
#
#        if cache:
#            models = self._get_all_from_mc(all_cache_key_list)
#
#            all_object = zip(model_id_list, all_cache_key_list)
#
#            for model_id, cache_key in all_object:
#
#                model = models.get(cache_key)
#
#                if not model:
#                    not_found_dict[model_id] = cache_key
#                else:
#                    all_found_item_dict[cache_key] = model
#                    
#
#        if len(not_found_dict.keys()) > 0:
#            session = Session()
#
#            objects = self._get_all_from_db(model_cls, not_found_dict.keys())
#            
#            found_item_dict = {}
#            for the_object in objects:
#                cache_key = not_found_dict.get(the_object.id)
#                found_item_dict[cache_key] = the_object
#                
#            self._write_all_to_mc(found_item_dict)
#            all_found_item_dict.update(found_item_dict)
#
#            session.close()
#
#        results = []
#        for k in all_cache_key_list:
#            results.append(all_found_item_dict.get(k))
#
#        return results
#    
#    def get_list_from_parent(self, parent_list, model_cls, id_key, cache=True):
#        if not parent_list or len(parent_list)==0:
#            return []
#
#        load_list = []
#        for parent in parent_list:
#            if hasattr(parent, id_key):
#                load_list.append(getattr(parent,id_key))
#            elif isinstance(parent, dict) and parent.has_key(id_key):
#                load_list.append(parent.get(id_key))
#            else:
#                # 保证id不会出现负值
#                load_list.append(-1)
#
#        return self.get_multi(model_cls, load_list, cache)
#
#    def update(self, model, write_db=True):
#        """
#        @param write_db: 是否写入数据库，否为只更新缓存
#        """
#        cache_key = self.mc.makeKey(model=str(model.__class__), model_id=model.id)
#        
#        self.mc.set(cache_key, model)
#        if write_db:
#            session = WriteSession()
#            session.merge(model)
#            session.commit()
#            session.close()
#
#
#    def update_multi(self, model_list):
#        session = WriteSession()
#        for model in model_list:
#            cache_key = self.mc.makeKey(model=str(model.__class__), model_id=model.id)
#            self.mc.set(cache_key, model)
#            session.merge(model)
#        session.commit()
#        session.close()
#        
#    def _write_to_mc(self, cache_key, value):
#        self.mc.set(cache_key, value)
#        
#    def _write_all_to_mc(self, dicts):
#        self.mc.set_multi(dicts)
#        
#    def _get_from_mc(self, cache_key):
#        t = time.time()
#        result = self.mc.get(cache_key)
#        application.log(time.time() - t, 'mc')
#        return result
#    
#    def _get_all_from_mc(self, cache_key_list):
#        t = time.time()
#        result = self.mc.get_multi(cache_key_list)
#        application.log(time.time() - t, 'mc', len(cache_key_list))
#        return result
#        
#    def _get_from_db(self, model_cls, model_id):
#        t = time.time()
#        session = Session()
#        result = session.query(model_cls).get(model_id)
#        application.log(time.time() - t)
#        return result
#    
#    def _get_all_from_db(self, model_cls, model_id_list):
#        t = time.time()
#        session = Session()
#        result = session.query(model_cls).filter(model_cls.id.in_(model_id_list)).all()
#        application.log(time.time() - t, 'db', len(model_id_list))
#        return result
