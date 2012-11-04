#coding:utf8
from unitofwork import UnitOfWork
from xweb.util import logging

class Entity(object):
    '''
    领域实体基类
    
    _version: 实体版本
    _belongs_to: BelongsTo的定义
    _default_values: 字段的默认值
    _primary_key: 主键名称
    _keys: 字段列表
    _types: 字段类型 如: {'name':long}
    
    @author: lifei
    @since: v1.0
    '''
    
    _version = 1
    _belongs_to = {}
    _default_values = {}
    _primary_key = 'id'
    _keys = [_primary_key]
    _types = {}
    
    def __init__(self, **kwargs):
        self._is_new = True
        self._is_delete = False
        self._is_dirty = False
        self._load_from_cache = False
        self._db = 'default'
        self._cache = 'default'
        self._dirty_keys = set()
        self._props = {}
        self._unitofwork = None
        self.load(**kwargs)
        
    def remove(self):
        self._is_delete = True
        self._is_dirty = True
                
    def load(self, **kwargs):
        cls = self.__class__
        for k in cls.allKeys():
            value = None
            if kwargs.has_key(k):
                value = kwargs.get(k)
            elif self._default_values.has_key(k):
                value = self._default_values.get(k)
            
            if cls._types.has_key(k):
                _format = cls._types.get(k)
                self.__dict__[k] = _format(value)
            else:
                self.__dict__[k] = value
        
    # protected methods       
    def getUnitOfWork(self):
        if not self._unitofwork:
            self._unitofwork = UnitOfWork.inst()
        return self._unitofwork
        
    # override methods
    def __getattr__(self, key):
        
        cls = self.__class__
        _belongs_to = cls._belongs_to
        
        if _belongs_to.has_key(key):
            return self.__getBelongsToEntity(key)
        
        if hasattr(self, key):
            return super(Entity, self).__getattribute__(key)
        elif cls._default_values.has_key(key):
            return cls._default_values.get(key)
        
        return None
    
    def __getBelongsToEntity(self, foreign_key):
        '''
        '''
        
        foreign_primary_key, foreign_class, foreign_id = self.getBelongsToInfo(foreign_key)
        unitofwork = self.getUnitOfWork()
        
        if not foreign_id:
            return None
        
        if self.disable_preload:
            return unitofwork.get(foreign_class, foreign_id)

        foreign_entity = unitofwork.getEntityInMemory(foreign_class, foreign_id)
        if foreign_entity:
            return foreign_entity
        
        # 多主键的实体禁用preload功能
        if type(foreign_primary_key) != str:
            return unitofwork.get(foreign_class, foreign_id)
        
        first_entity_id = self.getProps('first_entity_in_query', None)
        if  not first_entity_id:
            return unitofwork.get(foreign_class, foreign_id)
        
        if first_entity_id == self.getId():
            entity_ids_in_query = self.getProps('entity_ids_in_query', [])
        else:
            first_entity = unitofwork.getEntityInMemory(type(self), first_entity_id)
            if not first_entity:
                return unitofwork.get(foreign_class, foreign_id)
            entity_ids_in_query = first_entity.getPrpos('entity_ids_in_query', [])
            
        foreign_entity_ids = set()
        for current_entity_id in entity_ids_in_query:

            entity_in_query = unitofwork.getEntityInMemory(type(self), current_entity_id)
            if not entity_in_query:
                continue
            
            foreign_entity_id = getattr(entity_in_query, foreign_primary_key)
            foreign_entity_ids.add(foreign_entity_id)
            
        if foreign_entity_ids:
            foreign_entitys = unitofwork.getList(foreign_class, foreign_entity_ids)
            logging.debug("preload %s in %s" % (foreign_class.modelName(), str([foreign_entity.getId() for foreign_entity in foreign_entitys])))
            return unitofwork.getEntityInMemory(foreign_class, foreign_id)
        
        return unitofwork.get(foreign_class, foreign_id)
    
    def __setattr__(self, k, value):
        cls = self.__class__
        if cls._types.has_key(k):
            _format = cls._types.get(k)
            format_value = _format(value)
        else:
            format_value = value
            
        if format_value == self.__dict__.get(k):
            return
        
        self.__dict__[k] = format_value
        if k in cls._keys:
            self._is_dirty = True
            self._dirty_keys.add(k)
            
    def __str__(self):
        return "%s(%s)"%(self.modelName(), self.getId())
    
    def getPrimaryKey(self):
        return self.getId()
        
    def getId(self):
        primary_key = self.primaryKey()
        return getattr(self, primary_key)
            
    def getBelongsToInfo(self, foreign_key):
        
        cls = self.__class__
        _belongs_to = cls._belongs_to
        
        if _belongs_to.has_key(foreign_key):
            (foreign_primary_key, foreign_class) = _belongs_to.get(foreign_key)
            
            if type(foreign_primary_key) == tuple:
                foreign_value = tuple([ object.__getattribute__(self, key)  for key in foreign_primary_key])
            else:
                foreign_value = object.__getattribute__(self, foreign_primary_key)
                
            return foreign_primary_key, foreign_class, foreign_value
        
        return None, None, None
            
    def isNew(self):
        return self._is_new
    
    def isDirty(self):
        return self._is_dirty
    
    def isDelete(self):
        return self._is_delete
    
    def isLoadedFromCache(self):
        return self._load_from_cache
    
    def dirtyKeys(self):
        return self._dirty_keys
    
    def setProps(self, k, v):
        self._props[k] = v
        
    def getProps(self, k, v=None):
        return self._props.get(k, v)
    
    def onNew(self):
        pass
    
    def onDelete(self):
        pass
    
    def onUpdate(self):
        pass
        
    #==== class method ====
    @classmethod
    def createByBiz(cls, **kwargs):
        '''
        创建实体并自己注册到工作单元内
        @param cls: 实体类型
        '''
        
        if not kwargs.get('use_autoincrement_id'):
            primaryKey = cls.primaryKey()
            unitofwork = UnitOfWork.inst()
            if not kwargs.has_key(primaryKey):
                kwargs[primaryKey] = unitofwork.idgenerator().get()
            
        entity = cls(**kwargs)
        unitofwork.register(entity)
        return entity
        
    
    @classmethod
    def dbName(cls, **kwargs):
        '''
        database链接标识
        @param cls: 实体类型
        '''
        return 'default'
    
    @classmethod
    def cacheName(cls, **kwargs):
        '''
        cache链接标识
        @param cls: 实体类型
        '''
        return 'default'
    
    @classmethod
    def tableName(cls):
        if hasattr(cls, '_table_name') and cls._table_name:
            return cls._table_name
        else:
            return cls.__name__.lower()

    @classmethod
    def modelName(cls):
        return cls.__name__
        
    @classmethod
    def primaryKey(cls):
        return cls._primary_key
        
    @classmethod
    def defaultValues(cls, k):
        return cls._default_values.get(k)
        
    @classmethod
    def allKeys(cls):
        if not hasattr(cls, '_all_keys'):
            cls._all_keys = [cls._primary_key]
            cls._all_keys.extend(cls._keys)
        return cls._all_keys
    
    @classmethod
    def get(cls, entity_id):
        return UnitOfWork.inst().get(cls, entity_id)
    
    @classmethod
    def getList(cls, entity_ids):
        return UnitOfWork.inst().getList(cls, entity_ids)
    
    @classmethod
    def getListByCond(cls, condition='', *args):
        return UnitOfWork.inst().getListByCond(cls, condition, args)
    
    
class MultiIdEntity(Entity):
    '''
    多主键实体类
    
    @author: lifei
    @since: v1.0
    @note: 获取多干实体(#getList)性能比较低
    '''
    _keys = []
            
    def __str__(self):
        return "%s(%s)"%(self.modelName(), self.getId())
            
    def getId(self):
        primary_key = self.primaryKey()
        return tuple([getattr(self, k) for k in primary_key])
        
    #==== class method ====
    @classmethod
    def createByBiz(cls, **kwargs):
        '''
        创建实体并自己注册到工作单元内
        @param cls: 实体类型
        '''
        
        unitofwork = UnitOfWork.inst()
        entity = cls(**kwargs)
        unitofwork.register(entity)
        return entity
        
    @classmethod
    def allKeys(cls):
        if not hasattr(cls, '_all_keys'):
            cls._all_keys = list(cls._primary_key)
            cls._all_keys.extend(cls._keys)
        return cls._all_keys
    
    @classmethod
    def get(cls, **kwargs):
        return UnitOfWork.inst().get(cls, tuple([kwargs.get(key) for key in cls._primary_key]))
    
    @classmethod
    def getList(cls, entity_ids):
        raise Exception("MultiIdEntity DOES NOT SUPPORT getList")
    
    @classmethod
    def getListByCond(cls, condition, *args, **kwargs):
        return UnitOfWork.inst().getListByCond2(cls, condition, args, **kwargs)