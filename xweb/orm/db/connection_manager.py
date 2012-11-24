#coding:utf8
'''
Created on 2012-7-5

@author: lifei
'''


from exception import DefaultDBNotExists
from mysql import MySQLDBConnection
from xweb.util import logging

class ConnectionManager:
    '''
    采用LasyLoad的方式加载DB链接
    '''
    
    def __init__(self, conf):
        self.conf = conf
        self.connections = {}
        
    def get(self, name='default', read_only=False):
        
        if read_only:
            name = "%s_read" % name
            
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
            
            cls = driver2cls.get(driver) or MySQLDBConnection
            
            conn = cls(name, conf)
            self.connections[name] = conn
            logging.debug("[XWEB] INIT DB CONNECTION: %s", conn)
            
        return self.connections.get(name)
    
    def close(self):
        for k in self.connections:
            connection = self.connections.get(k)
            connection.close()
    