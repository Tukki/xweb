#coding:utf8
'''
Created on 2012-7-5

@author: lifei
'''
import MySQLdb #@UnresolvedImport
from connection import DBConnection
from xweb.orm.entity import Entity
import logging
import time

class MySQLDBConnection(DBConnection):
    """
    MySQL实现
    """
    
    def __init__(self, name, conf):
        
        kwargs = {}
        for k in conf:
            if k in ['user', 'host', 'passwd', 'db', 'charset', 'port']:
                kwargs[k] = conf.get(k)
        self.name = name
        self.desc =  "%s<mysql://%s:%s/%s>"%(self.name, conf.get('host', '127.0.0.1'),
                        conf.get('port', 3306), conf.get('db', 'test'))

        self._conn = MySQLdb.connect(**kwargs)
        self._conn.autocommit(False)
        
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
        
        return self._execute(sql, values)
        
    
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
        
        sql += " WHERE `%s`=%%s"%entity.primaryKey()
        values.append(getattr(entity, entity.primaryKey()))
        
        return self._execute(sql, values)
    
    def close(self):
        self._conn.close()
    
    def __str__(self):
        return self.desc