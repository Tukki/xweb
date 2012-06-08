#coding:utf8
'''
Created on 2012-6-3

@author: lifei
'''
class Entity(object):
    
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
        self._connection = 'default'
        self._cache = 'default'
        self._dirty_keys = set()
        self.load(**kwargs)
        
    def remove(self):
        self._is_delete = True
        self._is_dirty = True
                
    def load(self, **kwargs):
        cls = self.__class__
        for k in cls.allKeys():
            if kwargs.has_key(k):
                self.__dict__[k] = kwargs.get(k)
            elif self._default_values.has_key(k):
                self.__dict__[k] = self._default_values.get(k)
        
    def __getattr__(self, key):
        
        cls = self.__class__
        _belongs_to = cls._belongs_to
        
        if _belongs_to.has_key(key):
            (fkey, fcls) = _belongs_to.get(key)
            from orm.unitofwork import UnitOfWork
            unitofwork = UnitOfWork.inst()
            fid = super(Entity, self).__getattribute__(fkey)
            return unitofwork.get(fcls, fid)
        
        if hasattr(self, key):
            return super(Entity, self).__getattribute__(key)
        elif cls._default_values.has_key(key):
            return cls._default_values.get(key)
        
        return None
    
    def __setattr__(self, name, value):
        self.__dict__[name] = value
        if name in self.__class__._keys:
            self._is_dirty = True
            self._dirty_keys.add(name)
            
            
    def isNew(self):
        return self._is_new
    
    def isDirty(self):
        return self._is_dirty
    
    def isDelete(self):
        return self._is_delete
    
    def dirtyKeys(self):
        return self._dirty_keys
        
        
    #==== class method ====
    
    @classmethod
    def connection(cls, **kwargs):
        '''
        计算需要的db链接
        @param cls: 实体类型
        '''
        return 'default'
    
    @classmethod
    def cache(cls, **kwargs):
        '''
        计算需要的db链接
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
    def where(cls):
        pass
    
    @classmethod
    def get(cls, id):
        from orm.unitofwork import UnitOfWork
        return UnitOfWork.inst().get(cls, id)
        