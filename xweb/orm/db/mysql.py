#coding:utf8
'''
Created on 2012-7-5

@author: lifei
'''
try:
    import pymysql as mysql
except ImportError:
    import MySQLdb as mysql
    
from connection import DBConnection
from xweb.util import logging
import time

from pymysql.err import raise_mysql_exception, Warning, Error, \
    InterfaceError, DataError, DatabaseError, OperationalError, \
    IntegrityError, InternalError, NotSupportedError, ProgrammingError
from xweb.orm.field import Criteria

def generate_where_clause(primary_key, entity_id):
    
    if type(primary_key) == str:
        where_clause = "`%s`=%%s" % primary_key
        value = (entity_id, )
    else:
        where_clause = " AND ".join(["`%s`=%%s"]*len(primary_key)) % primary_key
        value = entity_id
        
    return where_clause, value


c_types = dict(eq='=', ne='<>', lt='<', le='<=', gt='>',
               ge='>=')

def generate_clause(c, table_map={}):
    
    if c.type in ['or', 'and']:
        args = []
        sqls = []
        for cr in c.data:
            sql, arg = generate_clause(cr, table_map)
            sqls.append(sql)
            args += arg
        
        ret = (" %s " % c.type).join(sqls)
        return "(%s)" % ret, args
    else:
    
        table_name = c.field.cls._table_name
        if not table_map.has_key(table_name):
            table_map[table_name] = "t%s" % len(table_map)
            
        alias_table_name = table_map.get(table_name)
        c_type = c_types.get(c.type, c.type)
        if type(c.data) in [list, tuple]:
            sql = "%s.%s %s (%s)" % (alias_table_name, c.field.column, c_type, ",".join(["%s"]*len(c.data)))
            return sql, c.data
        else:
            sql = "%s.%s%s%%s" % (alias_table_name, c.field.column, c_type)
            return sql, [c.data]
        

class MySQLDBConnection(DBConnection):
    """
    MySQL实现
    
    @param timeout: 数据库链接的超时时间
    """
    
    def __init__(self, name, conf):
        
        kwargs = {}
        for k in conf:
            if k in ['user', 'host', 'passwd', 'db', 'charset', 'port', 'timeout']:
                kwargs[k] = conf.get(k)
        self.name = name
        self.desc =  "%s<mysql://%s:%s/%s>"%(self.name, conf.get('host', '127.0.0.1'),
                        conf.get('port', 3306), conf.get('db', 'test'))
        
        self.connect_args = kwargs
        
    def connect(self):
        
        if not hasattr(self, '_conn') or not self._conn:
            self._conn = mysql.connect(**self.connect_args)
            self._conn.autocommit(True)
            self._conn.connect_timeout = self.connect_args.get('timeout', 10)
            
        return self._conn;
    
    def begin(self):
        if hasattr(self.connect(), 'begin'):
            self.connect().begin()
        else:
            self.execute("BEGIN")
        logging.debug("开启事务")
            
        
    def commit(self):
        self.connect().commit()
        
    def rollback(self):
        self.connect().rollback()
        
    def getEntity(self, cls, entity_id):
        
        primary_key = cls.primaryKey()
        
        columns = ["`%s`"%c for c in cls.getColumns()]
        if type(primary_key) == str:
        
            sql = "SELECT %s FROM `%s` WHERE `%s`=%%s limit 1"%(",".join(columns),
                cls.tableName(), primary_key)
            
            value = (entity_id, )
            
        else:
            
            where_clause, value = generate_where_clause(primary_key, entity_id)
        
            sql = "SELECT %s FROM `%s` WHERE %s limit 1"%(",".join(columns),
                cls.tableName(), where_clause)
            
        row = self.fetchRow(sql, *value)
            
        if not row:
            return None
        
        return self.createEntity(cls, row)
    
    def fetchEntityIds(self, cls, criteria, args=[]):
        
        assert isinstance(criteria, Criteria)
        
        table_map = {}
        condition, args = generate_clause(criteria, table_map)
        
        primary_key = cls.primaryKey()
        table_name = cls.tableName()
        alias_table_name = table_map.get(table_name)
        
        if not alias_table_name:
            raise ValueError()

        if type(primary_key) == str:
            sql = "SELECT `%s`.`%s` FROM `%s` WHERE %s"%(alias_table_name, primary_key,
                table_name, condition or '1=1')
            
            args = tuple(args)
            rows = self.fetchRows(sql, *args)
            
            if not rows:
                return []
            
            return [r[0] for r in rows]
        else:
            
            sql = "SELECT %s FROM `%s` WHERE %s"%( ",".join(["`%s`.`%s`" % (alias_table_name, k) 
                                                             for k in primary_key]),
                alias_table_name, condition or '1=1')
            
        
            args = tuple(args)
            rows = self.fetchRows(sql, *args)
            
            if not rows:
                return []
            
            return rows
        
        
    def queryRowsByCond(self, cls, condition, args=[]):
        
        columns = ["`%s`"%c for c in cls.getColumns()]
        sql = "SELECT `%s` FROM `%s` WHERE %s"%( "`,`".join(columns),
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
        
        columns = ["`%s`"%c for c in cls.getColumns()]
        sql = "SELECT %s FROM `%s` WHERE `%s` IN(%s)"%(",".join(columns),
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
        for k, field in entity.getFields().items():
            keys.append("`%s`"%field.column)
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
        
        cls = type(entity)
        
        table_name = cls.tableName()
        dirty_keys = entity.dirtyKeys()
        
        sql = "UPDATE `%s` SET "%table_name
        
        keys = []
        values = []
        for k in dirty_keys:
            field = cls.getFieldByName(k)
            keys.append("`%s`=%%s"%field.column)
            values.append(getattr(entity, k))
            
        sql += ",".join(keys)
        
        primary_key = cls.primaryKey()
        where_clause, where_value = generate_where_clause(primary_key, entity.getId())
        
        sql += " WHERE %s LIMIT 1" % where_clause
        values.extend(where_value)
        
        return self.execute(sql, values)
    
    def close(self):
        self._conn.close()
    
    def __str__(self):
        return self.desc
    
    
    def ping(self):
        self._conn.ping()

    
    def execute(self, sql, values=()):
        
        n = 0
        cursor = self.connect().cursor()
        try:
            t = time.time()
            cnt = 0
            while cnt < 2:
                cnt += 1
                try:
                    n = cursor.execute(sql, tuple(values))
                    t= time.time() - t
                    logging.debug("[XWEB] SQL: \"%s\", PARAMS: %s, ROWS: %s, TIME: %.1fms"%(sql,
                            str(values[:10]), n, t*1000))
                    return n
                except InterfaceError:
                    logging.debug("[XWEB] MYSQL RECONNECT...")
                    self.ping()
        finally:
            cursor.close()
        
        return False
    
    def fetchRow(self, sql, *args):
        
        cursor = self.connect().cursor()
        try:
            t = time.time()
            cnt = 0
            while cnt < 2:
                cnt += 1
                try:
                    cursor.execute(sql, tuple(args))
                    row = cursor.fetchone()
                    t= time.time() - t
                    logging.debug("[XWEB] SQL: \"%s\", PARAMS: %s, TIME: %.1fms"%(sql,
                            str(args[:10]), t*1000))
                    return row
                    break
                except InterfaceError:
                    logging.debug("[XWEB] MYSQL RECONNECT...")
                    self.ping()
        finally:
            cursor.close()
            
        return None
    
    def fetchRows(self, sql, *args):
        
        cursor = self.connect().cursor()
        
        try:
            t = time.time()
            cnt = 0
            while cnt < 2:
                cnt += 1
                try:
                    cursor.execute(sql, tuple(args))
                    row = cursor.fetchall()
                    t= time.time() - t
                    logging.debug("[XWEB] SQL: \"%s\", PARAMS: %s, TIME: %.1fms"%(sql,
                            str(args[:10]), t*1000))
                    return row
                    break
                except InterfaceError:
                    logging.debug("[XWEB] MYSQL RECONNECT...")
                    self.ping()
        finally:
            cursor.close()
            
        return None    