#coding:utf8
'''
Created on 2012-6-3

@author: lifei
'''

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
            
        self._db = None
    
    def createEntity(self, cls, row):
        kwargs = {}
        for k, v in zip(cls.getFields(), row):
            kwargs[k] = v
        entity = cls(**kwargs)
        entity._is_new = False
        entity._db = self.name
        entity._load_from_cache = False
        
        return entity
    
    def execute(self, sql, values):
        
        n = 0
        cursor = self.connect().cursor()
        
        try:
            t = time.time()
            n = cursor.execute(sql, tuple(values))
        finally:
            cursor.close()
            self.last_time = time.time()
            t= time.time() - t
            logging.debug("[XWEB] SQL: \"%s\", PARAMS: %s, ROWS: %s, TIME: %.1fms"%(sql,
                    str(values[:10]), n, t*1000))
        
        return n > 0
    
    def fetchRow(self, sql, *args):
        
        cursor = self.connect().cursor()
        
        try:
            t = time.time()
            cursor.execute(sql, args)
            self.last_time = time.time()
            row = cursor.fetchone()
            t= time.time() - t
            logging.debug("[XWEB] SQL: \"%s\", PARAMS: %s, TIME: %.1fms"%(sql,
                    str(args[:10]), t*1000))
            return row
        finally:
            cursor.close()
            
        return None
    
    def fetchRows(self, sql, *args):
        
        cursor = self.connect().cursor()
        
        try:
            t = time.time()
            cursor.execute(sql, args)
            self.last_time = time.time()
            row = cursor.fetchall()
            t = time.time() - t
            logging.debug("[XWEB] SQL: \"%s\", PARAMS: %s, ROWS: %s, TIME: %.1fms"%(sql,
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
    
    def begin(self):
        pass
    
    def commit(self):
        pass
    
    def rollback(self):
        pass
    


    