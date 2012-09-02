#coding:utf8
'''
Created on 2012-6-3

@author: lifei
'''

import MySQLdb
from exception import *
from xweb.util import logging
import time

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
    
    def createEntity(self, cls, row):
        kwargs = {}
        for k, v in zip(cls.allKeys(), row):
            kwargs[k] = v
        entity = cls(**kwargs)
        entity._is_new = False
        entity._db = self.name
        entity._load_from_cache = False
        
        return entity
    
    def execute(self, sql, values):
        
        n = 0
        cursor = self._conn.cursor()
        
        try:
            t = time.time()
            n = cursor.execute(sql, tuple(values))
            t= time.time() - t
        finally:
            cursor.close()
            logging.debug("sql: \"%s\", params: %s, rows: %s, time: %.1fms"%(sql,
                    str(values), n, t*1000))
        
        return n > 0
    
    def fetchRow(self, sql, *args):
        
        cursor = self._conn.cursor()
        
        try:
            t = time.time()
            cursor.execute(sql, args)
            row = cursor.fetchone()
            t= time.time() - t
            logging.debug("sql: \"%s\", params: %s, time: %.1fms"%(sql,
                    str(args), t*1000))
            return row
        finally:
            cursor.close()
            
        return None
    
    def fetchRows(self, sql, *args):
        
        cursor = self._conn.cursor()
        
        try:
            t = time.time()
            cursor.execute(sql, args)
            row = cursor.fetchall()
            t = time.time() - t
            logging.debug("sql: \"%s\", params: %s, rows: %s, time: %.1fms"%(sql,
                    str(args[:10]), len(row), t*1000))
            return row
        finally:
            cursor.close()
            
        return None    
      
    def fetchEntityIds(self, cls, condition, args):
        return None
        
    def getEntity(self, cls, id):
        return None  
    
    def getEntityList(self, cls, ids):
        pass
    
    def insert(self, entity):
        pass
    
    def update(self, entity):
        pass
    
    def delete(self, entity):
        pass
    
    def log(self):
        pass
    
    def close(self):
        pass
    


    