#coding:utf8
'''
Created on 2012-7-5

@author: lifei
'''
try:
    import MySQLdb as mysql
except:
    import pymysql as mysql
    
from connection import DBConnection
from xweb.util import logging
import time

def generate_where_clause(primary_key, entity_id):
    
    if type(primary_key) == str:
        where_clause = "`%s`=%%s" % primary_key
        value = (entity_id, )
    else:
        where_clause = " AND ".join(["`%s`=%%s"]*len(primary_key)) % primary_key
        value = entity_id
        
    return where_clause, value
        
        

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
        
        self.connect_args = kwargs
        self.timeout = conf.get('timeout') or 10
        self.last_time = time.time()
        
    def isTimeout(self):
        return time.time() - self.last_time > self.timeout
        
    def connect(self):
        
        if hasattr(self, '_conn') and self._conn:
            if not self.isTimeout():
                return self._conn
            else:
                self._conn.close()
                logging.debug("reconnect mysql server")
            
        self._conn = mysql.connect(**self.connect_args)
        self._conn.autocommit(False)
        self.timeout = time.time()
            
        return self._conn;
    
    def begin(self):
        if hasattr(self.connect(), 'begin'):
            self.connect().begin()
        
    def commit(self):
        self.connect().commit()
        
    def rollback(self):
        self.connect().rollback()
        
    def getEntity(self, cls, entity_id):
        
        primary_key = cls.primaryKey()
        
        if type(primary_key) == str:
        
            sql = "select %s from `%s` where `%s`=%%s limit 1"%(",".join(cls.allKeys()),
                cls.tableName(), primary_key)
            
            value = (entity_id, )
            
        else:
            
            where_clause, value = generate_where_clause(primary_key, entity_id)
        
            sql = "select %s from `%s` where %s limit 1"%(",".join(cls.allKeys()),
                cls.tableName(), where_clause)
            
        row = self.fetchRow(sql, *value)
            
        if not row:
            return None
        
        kwargs = {}
        for k, v in zip(cls.allKeys(), row):
            kwargs[k] = v
        
        return self.createEntity(cls, row)
          
    def fetchEntityIds(self, cls, condition, args=[]):
        
        primary_key = cls.primaryKey()
        
        if type(primary_key) == str:
            
            sql = "select %s from `%s` where %s"%(primary_key,
                cls.tableName(), condition or '1=1')
            
            args = tuple(args)
            rows = self.fetchRows(sql, *args)
            
            if not rows:
                return []
            
            return [r[0] for r in rows]
        else:
            
            sql = "select %s from `%s` where %s"%( ",".join(primary_key),
                cls.tableName(), condition or '1=1')
            
        
            args = tuple(args)
            rows = self.fetchRows(sql, *args)
            
            if not rows:
                return []
            
            return rows
        
        
    def queryRowsByCond(self, cls, condition, args=[]):
        
        sql = "select `%s` from `%s` where %s"%( "`,`".join(cls.allKeys()),
            cls.tableName(), condition or '1=1')
        
        args = tuple(args)
        rows = self.fetchRows(sql, *args)
        
        if not rows:
            return []
        
        return rows
           
    def getEntityList(self, cls, ids):
        
        if not ids:
            return []
        
        keys = []
        values = []
        
        for id in ids:
            keys.append("%s")
            values.append(id)
        
        sql = "select %s from `%s` where `%s` in(%s)"%(",".join(cls.allKeys()),
            cls.tableName(), cls.primaryKey(), ','.join(keys))
        
        args = tuple(values)
        rows = self.fetchRows(sql, *args)

        if not rows:
            return []
        
        return [self.createEntity(cls, row) for row in rows]
    
    def insert(self, entity):
        from xweb.orm.entity import Entity
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
        
        return self.execute(sql, values)
        
    
    def update(self, entity):
        from xweb.orm.entity import Entity
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
        
        primary_key = entity.primaryKey()
        where_clause, where_value = generate_where_clause(primary_key, entity.getId())
        
        sql += " WHERE %s LIMIT 1" % where_clause
        values.extend(where_value)
        
        return self.execute(sql, values)
    
    def close(self):
        self._conn.close()
    
    def __str__(self):
        return self.desc