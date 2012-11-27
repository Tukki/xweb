#coding:utf8
from unitofwork import UnitOfWork
from xweb.util import logging, BlockProfiler
from field import XField
from xweb.orm.field import XBelongsToField, Criteria, QueryCriteria

class Entity(object):
    '''
    领域实体基类
    
    @note: 需要继承的使用保护
    
    _version: 实体版本
    _primary_key: 主键名称
    
    @author: lifei
    @since: v1.0
    '''
    
    _version = 1
    _primary_key = 'id'
    _cache_name = 'default'
    disable_preload = False
    
    
    # protected method
    
    def _getBelongsToInfo(self, name):
        '''获取指定属性的belongsto配置信息
        
        @param name: 属性/字段名称
        
        '''
        
        field = self.getBelongsToFieldByName(name)
        
        if not field:
            return None, None, None
        
        (foreign_primary_key, foreign_class) = field.key, field.cls
        
        if type(foreign_primary_key) == tuple:
            foreign_value = tuple([ object.__getattribute__(self, key)  for key in foreign_primary_key])
        else:
            foreign_value = object.__getattribute__(self, foreign_primary_key)
            
        return foreign_primary_key, foreign_class, foreign_value
    
    @classmethod
    def registerToXWEB(cls):
        '''
        '''
    
    def __init__(self, **kwargs):
        self._is_new = True
        self._is_delete = False
        self._is_dirty = False
        self._load_from_cache = False
        self._db = 'default'
        self._cache = 'default'
        self._dirty_keys = set()
        self._props = {}
        self.__errors = {}
        self._unitofwork = None
        self._init(**kwargs)
        
    def remove(self):
        self._is_delete = True
        self._is_dirty = False
                
    def _init(self, **kwargs):
        cls = self.__class__
        for k,v in cls.getFields().items():
            self.__dict__[k] = v.format(kwargs.get(k))
                
    def updateFields(self, **kwargs):
        cls = self.__class__
        for k,v in cls.getFields().items():
            if kwargs.has_key(k):
                self.__dict__[k] = v.format(kwargs.get(k))
        
    # protected methods       
    def getUnitOfWork(self):
        if not self._unitofwork:
            self._unitofwork = UnitOfWork.inst()
        return self._unitofwork
    
    
    #override
    def __getattribute__(self, *args, **kwargs):
        
        if args and args[0] != 'hasBelongsToField' and self.hasBelongsToField(args[0]):
            return self.__getBelongsToEntity(args[0])
        return object.__getattribute__(self, *args, **kwargs)
    
    def __getBelongsToEntity(self, name):
        '''
        '''
        
        foreign_key, foreign_class, foreign_id = self._getBelongsToInfo(name)
        unitofwork = self.getUnitOfWork()
        
        if not foreign_id:
            return None
        
        if self.disable_preload:
            return unitofwork.get(foreign_class, foreign_id)

        foreign_entity = unitofwork.getEntityInMemory(foreign_class, foreign_id)
        if foreign_entity:
            return foreign_entity
        
        # 多主键的实体禁用preload功能
        if type(foreign_key) != str:
            return unitofwork.get(foreign_class, foreign_id)
        
        first_entity_id = self.getProps('first_entity_in_query')
        if  not first_entity_id:
            return unitofwork.get(foreign_class, foreign_id)
        
        if first_entity_id == self.getId():
            entity_ids_in_query = self.getProps('entity_ids_in_query', [])
        else:
            first_entity = unitofwork.getEntityInMemory(type(self), first_entity_id)
            if not first_entity:
                return unitofwork.get(foreign_class, foreign_id)
            entity_ids_in_query = first_entity.getProps('entity_ids_in_query', [])
            
        foreign_entity_infos = {}
        for current_entity_id in entity_ids_in_query:

            entity_in_query = unitofwork.getEntityInMemory(type(self), current_entity_id)
            if not entity_in_query:
                continue
            
            sub_foreign_class, sub_foreign_id = entity_in_query._getBelongsToInfo(name)[-2:]
            
            if not foreign_entity_infos.has_key(sub_foreign_class):
                foreign_entity_infos[sub_foreign_class] = [sub_foreign_id]
            else:
                foreign_entity_infos[sub_foreign_class].append(sub_foreign_id)
                
        if foreign_entity_infos:
            
            for sub_foreign_class, sub_foreign_ids in foreign_entity_infos.items():
                foreign_entitys = unitofwork.getList(sub_foreign_class, sub_foreign_ids)
                logging.debug("[XWEB] PRELOAD %s in %s" % 
                              (sub_foreign_class.modelName(),
                               str([foreign_entity.getId() for foreign_entity in foreign_entitys])))
                
            return unitofwork.getEntityInMemory(foreign_class, foreign_id)
        
        return unitofwork.get(foreign_class, foreign_id)
    
    def __setattr__(self, k, value):
        
        if self.hasField(k):
            field = self.getFieldByName(k)
            value = field.format(value)
            if value == self.__dict__.get(k):
                return
            
            self._is_dirty = True
            self._dirty_keys.add(k)
        
        self.__dict__[k] = value
            
    def __str__(self):
        return "%s(%s)"%(self.modelName(), self.getId())
        
    def getId(self):
        primary_key = self.primaryKey()
        return getattr(self, primary_key)
            
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
    
    def doValidate(self):
        '''验证所有的验证器是否通过，将错误保存在__errors
        '''
        is_good = True
        self.__errors.clear()
        for k, v in self.getFields().items():
            result = v.validate(getattr(self, k))
            if result is not None:
                if not self.__errors.has_key(k):
                    self.__errors[k] = []
                    
                self.__errors[k] += result
                is_good = False
                    
        return is_good
    
    def getErrors(self):
        return self.__errors

    def clearErrors(self):
        self.__errors.clear()
        
    def getCacheDict(self):
        
        cache_dict = {'_db': self._db}
        
        for k in self.getFields().keys():
            cache_dict[k] = getattr(self, k)
            
        return cache_dict
        
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
    def getFields(cls, is_belongs_to=False):
            
        if is_belongs_to:
            return cls._belongs_to_fields
        else:
            return cls._fields
    
    @classmethod
    def hasField(cls, name):
        return cls.getFields().has_key(name)
        
    @classmethod
    def getBelongsToField(cls):
        return cls.getFields(True)
    
    @classmethod
    def hasBelongsToField(cls, name):
        return cls.getFields(True).has_key(name)
    
    @classmethod
    def getBelongsToFieldByName(cls, name):
        return cls.getBelongsToField()[name]
        
    @classmethod
    def getColumns(cls):
        return [f.column for f in cls.getFields().values()]
    
    @classmethod
    def getFieldByName(cls, name):
        return cls.getFields()[name]
    
    @classmethod
    def get(cls, entity_id):
        return UnitOfWork.inst().get(cls, entity_id)
    
    @classmethod
    def getList(cls, entity_ids):
        return UnitOfWork.inst().getList(cls, entity_ids)
    
    @classmethod
    def getListByCond(cls, *args, **kws):
        cr = QueryCriteria(cls).filter(*args)
        
        if kws.has_key('limit'):
            cr.limit(int(kws['limit']))
        
        if kws.has_key('offset'):
            cr.offset(int(kws['offset']))
            
        return UnitOfWork.inst().getListByCond(cr)
    
    @classmethod
    def query(cls, *args):
        return QueryCriteria(cls).query(*args)
    
    @classmethod
    def filter(cls, *args):
        return QueryCriteria(cls).filter(*args)
    
    
class ShardingEntity(Entity):
    """
    分片存储的实体
    """
    
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
    def get(cls, **kwargs):
        return UnitOfWork.inst().get(cls, tuple([kwargs.get(key) for key in cls._primary_key]))
    
    @classmethod
    def getList(cls, entity_ids):
        raise Exception("MultiIdEntity DOES NOT SUPPORT getList")
    
    @classmethod
    def getListByCond(cls, condition, *args, **kwargs):
        return UnitOfWork.inst().getListByCond2(cls, condition, args, **kwargs)
    
