#coding:utf8
'''
Created on 2012-7-5

@author: lifei
'''
try:
    import MySQLdb as mysql
    from MySQLdb import InterfaceError, OperationalError
except ImportError:
    import pymysql as mysql
    from pymysql.err import InterfaceError, OperationalError
    
    
from connection import DBConnection
from xweb.util import logging
import time

from xweb.orm.field import Criteria, QueryCriteria, WhereCriteria, XField,\
    SelectCriteria
from xweb.orm.entity import Entity

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
            if cr.type in ['or', 'and'] and cr.type != c.type:
                sql = "(%s)" % sql
                
            sqls.append(sql)
            args += arg
        
        sql = (" %s " % c.type).join(sqls)
        
        if isinstance(c, QueryCriteria):
            
            if sql:
                sql = "WHERE %s" % sql
            
            if c.order_by:
                order_bys = []
                for cr in c.order_by:
                    alias_tbl_name = get_table_names(cr, table_map)[-1]
                    order_bys.append("`%s`.`%s` %s" % (alias_tbl_name, cr.field.column, cr.type))
                    
                
                sql += " order by %s" % (",".join(order_bys))
                
            if c._limit:
                sql += " limit"
                if c._offset:
                    sql += " %s," % c._offset
                sql += " %s" % c._limit
                
        return sql, args
    else:
    
        alias_table_name = get_table_names(c.field, table_map)[-1]
        c_type = c_types.get(c.type, c.type)
        if type(c.data) in [list, tuple]:
            sql = "`%s`.`%s` %s (%s)" % (alias_table_name, c.field.column, c_type, ",".join(["%s"]*len(c.data)))
            return sql, c.data
        else:
            sql = "`%s`.`%s`%s%%s" % (alias_table_name, c.field.column, c_type)
            return sql, [c.data]
    
def get_table_names(m, table_map):
    
        if isinstance(m, XField):
            table_name = m.cls.tableName()
        elif isinstance(m, type) and hasattr(m, 'tableName'):
            table_name = m.tableName()
        elif isinstance(m, Criteria):
            if hasattr(m, 'field'):
                table_name = m.field.cls.tableName()
            elif hasattr(m, 'entity_cls'):
                table_name = m.entity_cls.cls.tableName()
            else:
                raise ValueError("BAD TABLE NAME TYPE")
        else:
            raise ValueError("BAD TABLE NAME TYPE")

        if not table_map.has_key(table_name):
            table_map[table_name] = "t%s" % len(table_map)
            
        return table_name, table_map.get(table_name)
    
        
def generate_join_clause(cr, table_map):
    
    join_tbl_name, join_alias_tbl_name = get_table_names(cr.entity_cls, table_map)
    if not cr.data:
        return ""
    
    joins = []
    args = []
    for c in cr.data:
        tbl_name, alias_tbl_name = get_table_names(c.field, table_map)
        
        if isinstance(c.data, XField):
            tbl2_name, alias_tbl2_name = get_table_names(c.data, table_map)
            if alias_tbl2_name == alias_tbl_name:
                raise ValueError("DO NOT SUPPORT JOIN A TABLE ITSELF!")
            
            if join_tbl_name not in [tbl_name, tbl2_name]:
                raise ValueError("JOIN需要至少一个表与主表有关联")
            
            c_type = c_types.get(c.type)
            if not c_type:
                raise ValueError("ERROR JOIN COMPARE TYPE")
            
            join = "`%s`.`%s`%s`%s`.`%s`" % (alias_tbl_name, c.field.column,
                                             c_type,
                                             alias_tbl2_name, c.data.column)
            
            joins.append(join)
        else:
            if type(c.data) in [list, tuple]:
                join = "`%s`.`%s` %s (%s)" % (alias_tbl_name, c.field.column, 
                                             c_type, ",".join(["%s"]*len(c.data)))
                
                joins.append(join)
                args += c.data
            else:
                join = "`%s`.`%s`%s%%s" % (alias_tbl_name, cr.field.column, c_type)
                joins.append(join)
                args.append(c.data)
                
    join_sql = " and ".join(joins)
    
    return "JOIN `%s` as `%s` ON %s " % (join_tbl_name, join_alias_tbl_name, join_sql), args
        
def generate_select_clause(cr, table_map):
    
    if not cr.select:
        return "*"
    
    sqls = []
    for sfc in cr.select:
        
        if isinstance(sfc, XField):
            field = sfc
            tbl_name = get_table_names(field, table_map)[-1]
            sql = "`%s`.`%s` as `%s_%s`" % (tbl_name, field.column, tbl_name, field.column)
        elif isinstance(sfc, SelectCriteria):
            if sfc.type in ['count', 'sum']:
                if isinstance(sfc.data, XField):
                    field = sfc.data
                    tbl_name = get_table_names(field, table_map)[-1]
                    sql = "%s(`%s`.`%s`) as %s_%s_%s" % (sfc.type.upper(), tbl_name, field.column,
                                                      sfc.type.lower(), tbl_name, field.column,)
                else:
                    sql = "%s(%s)" % (sfc.type.upper(), sfc.data)
                    
            else:
                continue
        
        sqls.append(sql)
    
    return ",".join(sqls)
        
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
    
    def fetchEntityIds(self, criteria):
        
        assert isinstance(criteria, QueryCriteria)
        
        cls = criteria.entity_cls
        primary_key = cls.primaryKey()
        tbl_name = cls.tableName()
        table_map = {}
        table_map[tbl_name] = 't0'
        joins = []
        args = []
        if criteria._join:
            for j in criteria._join:
                sql, arg = generate_join_clause(j, table_map)
                joins.append(sql)
                args += arg
                
            join_sql = " ".join(joins)
        else:
            join_sql = ""
                
        where_sql, arg = generate_clause(criteria, table_map)
        args += arg
        
        if type(primary_key) == tuple:
            criteria.select = [getattr(cls, k) for k in primary_key]
        else:
            criteria.select = [getattr(cls, primary_key)]
            
        select_sql = generate_select_clause(criteria, table_map)
        
        sql = "SELECT %s FROM `%s` as `t0` %s %s"%(select_sql,
                tbl_name, join_sql, where_sql)
            
        args = tuple(args)
        rows = self.fetchRows(sql, *args)
        
        if not rows:
            return []
        
        if type(primary_key) == tuple:
            return rows
        else:
            return [r[0] for r in rows]
            
        
        
    def queryRowsByCond(self, cls, condition, args=[]):
        
        columns = ["`%s`"%c for c in cls.getColumns()]
        sql = "SELECT `%s` FROM `%s` WHERE %s"%( "`,`".join(columns),
            cls.tableName(), condition or '1=1')
        
        args = tuple(args)
        rows = self.fetchRows(sql, *args)
        
        if not rows:
            return []
        
        return rows
        
    def fetchRowByCond(self, criteria):
        
        assert isinstance(criteria, QueryCriteria)
        tbl_name = criteria.entity_cls.tableName()
        table_map = {}
        table_map[tbl_name] = 't0'
        joins = []
        args = []
        if criteria._join:
            for j in criteria._join:
                sql, arg = generate_join_clause(j, table_map)
                joins.append(sql)
                args += arg
                
            join_sql = " ".join(joins)
        else:
            join_sql = ""
                
        where_sql, arg = generate_clause(criteria, table_map)
        args += arg
        
        select_sql = generate_select_clause(criteria, table_map)
        
        sql = "SELECT %s FROM `%s` as t0 %s %s" % (select_sql, tbl_name, join_sql, where_sql)
        
        args = tuple(args)
        return self.fetchRow(sql, *args)
        
    def fetchRowsByCond(self, criteria):
        
        assert isinstance(criteria, QueryCriteria)
        tbl_name = criteria.entity_cls.tableName()
        table_map = {}
        table_map[tbl_name] = 't0'
        joins = []
        args = []
        if criteria._join:
            for j in criteria._join:
                sql, arg = generate_join_clause(j, table_map)
                joins.append(sql)
                args += arg
                
            join_sql = " ".join(joins)
        else:
            join_sql = ""
                
        where_sql, arg = generate_clause(criteria, table_map)
        args += arg
        
        select_sql = generate_select_clause(criteria, table_map)
        
        sql = "SELECT %s FROM `%s` as t0 %s %s" % (select_sql, tbl_name, join_sql, where_sql)
        
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
                    logging.debug("[XWEB] FETCH ROWS SQL: \"%s\", PARAMS: %s, ROWS: %s, TIME: %.1fms"%(sql,
                            str(values[:10]), n, t*1000))
                    return n
                except InterfaceError, OperationalError:
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
                    logging.debug("[XWEB] FETCH ROW SQL: \"%s\", PARAMS: %s, TIME: %.1fms"%(sql,
                            str(args[:10]), t*1000))
                    return row
                    break
                except InterfaceError, OperationalError:
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
                except InterfaceError, OperationalError:
                    logging.debug("[XWEB] MYSQL RECONNECT...")
                    self.ping()
        finally:
            cursor.close()
            
        return None    