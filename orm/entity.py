#coding:utf8

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
    def _getUnitOfWork(self):
        if not self._unitofwork:
            from orm.unitofwork import UnitOfWork
            self._unitofwork = UnitOfWork.inst()
        return self._unitofwork
        
    # override methods
    def __getattr__(self, key):
        
        entity = self._getUnitOfWork().getBelongsToEntity(self, key)
        
        if entity:
            return entity
        
        cls = self.__class__
        
        if hasattr(self, key):
            return super(Entity, self).__getattribute__(key)
        elif cls._default_values.has_key(key):
            return cls._default_values.get(key)
        
        return None
    
    def __setattr__(self, k, value):
        cls = self.__class__
        if cls._types.has_key(k):
            _format = cls._types.get(k)
            self.__dict__[k] = _format(value)
        else:
            self.__dict__[k] = value
            
        if k in cls._keys:
            self._is_dirty = True
            self._dirty_keys.add(k)
            
    def __str__(self):
        return "%s(%s)"%(self.modelName(), self.getPrimaryKey())
            
    def getPrimaryKey(self):
        primary_key = self.primaryKey()
        
        if not hasattr(self, primary_key):
            raise Exception("primary key of %s is not set"%self.modelName())
        
        return getattr(self, primary_key)
            
    def getBelongsToInfo(self, foreign_key):
        
        cls = self.__class__
        _belongs_to = cls._belongs_to
        
        if _belongs_to.has_key(foreign_key):
            (fkey, fcls) = _belongs_to.get(foreign_key)
            fid =  super(Entity, self).__getattribute__(fkey)
            
            return fkey, fcls, fid
        
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
        
        if not kwargs.get('use_autoincrement_id'):
            from orm.unitofwork import UnitOfWork
            primaryKey = cls.primaryKey()
            unitofwork = UnitOfWork.inst()
            
            if not kwargs.has_key(primaryKey):
                kwargs[primaryKey] = unitofwork.idgenerator.get()
            
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
    def get(cls, id):
        from orm.unitofwork import UnitOfWork
        return UnitOfWork.inst().get(cls, id)
    
    @classmethod
    def getAll(cls, condition, args=[]):
        from orm.unitofwork import UnitOfWork
        return UnitOfWork.inst().getAllByCond(cls, condition, args)