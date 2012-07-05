'''
Created on 2012-7-5

@author: lifei
'''

import logging
from exception import DefaultDBNotExists
from mysql import MySQLDBConnection

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
    