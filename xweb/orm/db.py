#coding:utf8
'''
Created on 2012-6-3

@author: lifei
'''

import MySQLdb #@UnresolvedImport
from orm.entity import Entity
import logging

class DefaultDBNotExists(Exception):
    pass

class DBConnection:
    '''
    DBConnection的基类
    主要维护ORM数据读取，写入等操作的代码
    每一种的数据库类型或者NoSQL类型需要继承本类并实现相关代码
    '''
    
    def __init__(self, conf):
        self.conf = conf
        driver = conf.get('driver')
        if not driver:
            driver = 'mysql'
            
        self._db = MySQLdb.connect(host="localhost",user="root",passwd="",db="test",charset="utf8")
    
    def _createEntity(self, cls, row):
        kwargs = {}
        for k, v in zip(cls.allKeys(), row):
            kwargs[k] = v
        entity = cls(**kwargs)
        entity._is_new = False
        entity._db = self.name
        entity._load_from_cache = False
        
        return entity
        
    def queryOne(self, cls, id):
        return None      
      
    def queryIds(self, cls, condition, args):
        return None
    
    def queryAll(self, cls, ids):
        pass
    
    def insert(self, entity):
        pass
    
    def update(self, entity):
        pass
    
    def delete(self, entity):
        pass
    
    def log(self):
        pass
    
    @classmethod
    def build(cls, name, conf):
        driver = conf.get('driver')            
        driver2cls = {
            'mysql': MySQLDBConnection
            }
        
        cls = driver2cls.get(driver)
        
        if not cls:
            cls = MySQLDBConnection
            
        return cls(conf, name)
    
class MySQLDBConnection(DBConnection):
    """
    MySQL实现
    """
    
    def __init__(self, name, conf):
        
        kwargs = {}
        for k in conf:
            if k in ['user', 'host', 'passwd', 'db', 'charset']:
                kwargs[k] = conf.get(k)
        self.name = name
        self._conn = MySQLdb.connect(**kwargs)
        self._conn.autocommit(True)
        
    def connect(self):
        return self._conn;
        
    def queryOne(self, cls, id): #@ReservedAssignment
        
        sql = "select %s from `%s` where `%s`=%%s limit 1"%(",".join(cls.allKeys()),
            cls.tableName(), cls.primaryKey())
        
        cursor = self._conn.cursor()
        cursor.execute(sql, (id,))
        row = cursor.fetchone()
        cursor.close()
        
        if not row:
            return None
        
        kwargs = {}
        for k, v in zip(cls.allKeys(), row):
            kwargs[k] = v
        
        return self._createEntity(cls, row)
          
    def queryIds(self, cls, condition, args=[]): #@ReservedAssignment
            
        sql = "select %s from `%s` where %s"%(cls.primaryKey(),
            cls.tableName(), condition or '1=1')
        
        cursor = self._conn.cursor()
        cursor.execute(sql, tuple(args))
        row = cursor.fetchall()
        cursor.close()
        
        if not row:
            return []
        
        return [r[0] for r in row]
           
    def queryAll(self, cls, ids): #@ReservedAssignment
        
        if not ids:
            return []
        
        keys = []
        values = []
        
        for id in ids:
            keys.append("%s")
            values.append(id)
        
        sql = "select %s from `%s` where `%s` in(%s)"%(",".join(cls.allKeys()),
            cls.tableName(), cls.primaryKey(), ','.join(keys))
        
        cursor = self._conn.cursor()
        cursor.execute(sql, tuple(values))
        rows = cursor.fetchall()
        cursor.close()
        
        if not rows:
            return []
        
        return [self._createEntity(cls, row) for row in rows]
    
    def insert(self, entity):
        if not isinstance(entity, Entity):
            return False
        
        if entity.isDelete():
            return False
        
        if not entity.isNew():
            return False
        
        sql = "INSERT INTO `%s` ("%entity.tableName()
        
        keys = []
        place_holder = []
        values = []
        for k in entity.allKeys():
            keys.append("`%s`"%k)
            place_holder.append("%s")
            values.append(getattr(entity, k))
            
        sql += ",".join(keys)
        
        sql += ") VALUES ("
        sql += ",".join(place_holder)
        sql += ')'
        
        cursor = self._conn.cursor()
        n = cursor.execute(sql, tuple(values))
        cursor.close()
        
        return n == 1
        
    
    def update(self, entity):
        if not isinstance(entity, Entity):
            return False
        
        if not entity.isDirty():
            return False
        
        if entity.isDelete():
            return False
        
        if entity.isNew():
            return False
        
        table_name = entity.tableName()
        dirty_keys = entity.dirtyKeys()
        
        sql = "UPDATE `%s` SET "%table_name
        
        keys = []
        values = []
        for k in dirty_keys:
            keys.append("`%s`=%%s"%k)
            values.append(getattr(entity, k))
            
        sql += ",".join(keys)
        
        sql += " WHERE `%s`=%s"%(entity.primaryKey(), getattr(entity, entity.primaryKey()))
        
        cursor = self._conn.cursor()
        n = cursor.execute(sql, tuple(values))
        cursor.close()
        
        return n == 1


class ConnectionManager:
    '''
    采用LasyLoad的方式加载DB链接
    '''
    
    def __init__(self, conf):
        self.conf = conf
        self.connections = {}
        
    def get(self, name):
        if not self.conf.has_key(name):
            if not self.conf.has_key('default'):
                raise DefaultDBNotExists()
            return self.get('default')
        
        if not self.connections.has_key(name):
            
            conf = self.conf.get(name)
            
            driver = conf.get('driver')            
            driver2cls = {
                'mysql': MySQLDBConnection
                }
            
            cls = driver2cls.get(driver)
            
            if not cls:
                cls = MySQLDBConnection
                
            conn = cls(name, conf)
            self.connections[name] = conn
            logging.debug("init db connection: %s"%conn)
            
        return self.connections.get(name)
    
    def close(self):
        for k in self.connections:
            connection = self.connections.get(k)
            connection.close()
        