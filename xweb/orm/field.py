

class Criteria:
    pass
        
        
class WhereCriteria(Criteria):
    
    def __init__(self, t, data=[], field=None):
        self.type = t
        self.data = data
        self.field = field
        
        
class AndCriteria(Criteria):
    
    def __init__(self, data=[]):
        self.type = 'and'
        self.data = data
        
        
class OrCriteria(Criteria):
    
    def __init__(self, data=[]):
        self.type = 'or'
        self.data = data
        
        
class JoinCriteria(AndCriteria):
    
    def __init__(self, entity_cls, data=[]):
        self.entity_cls = entity_cls
        self.data = data
        
        
class OderByCriteria(Criteria):
    
    def __init__(self, field, t=''):
        self.field = field
        self.type = t
    
class QueryCriteria(AndCriteria):
    
    def __init__(self, entity_cls):
        self.entity_cls = entity_cls
        self.select = []
        self._join = []
        self.data = []
        self.order_by = []
        self._offset = 0
        self._limit = 0
        self.type = 'and'
        
    def query(self, *args):
        self.select = args
        return self
        
    def join(self, entity_cls, *args):
        self._join.append(JoinCriteria(entity_cls, args))
        return self
        
    def filter(self, *args):
        self.data += args
        return self
    
    def orderBy(self, *args):
        for a in args:
            if not isinstance(a, OderByCriteria):
                a = OderByCriteria(a)
                
            self.order_by.append(a)
            
        return self
    
    def limit(self, limit):
        self._limit = limit
        return self
        
    def offset(self, offset):
        self._offset = offset
        return self
    
    def all(self):
        from xweb.orm.unitofwork import UnitOfWork
        return UnitOfWork.inst().getListByCond(self)
    
    def rows(self):
        from xweb.orm.unitofwork import UnitOfWork
        return UnitOfWork.inst().fetchRowsByCond(self)
    
        
        
def or_(*args):
    return Criteria('or', args)

def and_(*args):
    return Criteria('and', args)

def desc(field):
    return OderByCriteria(field, 'DESC')

class XField:
    
    def __init__(self, **kws):
        self.column = kws.get('column')
        self.default_value = kws.get('default')
        self.can_null = kws.get('null', True)
        self.cls = None
        
    def _format(self, value):
        raise RuntimeError("Unsupport")
    
    def format(self, value):
        
        if value is None:
            if self.default_value is None and not self.can_null:
                #raise ValueError("%s can not be null", self.column)
                return None
            else:
                return self.default_value
        
        return self._format(value)
    
    def like(self, s):
        return WhereCriteria('like', s, self)
    
    def in_(self, s):
        return WhereCriteria('in', s, self)
    
    def between(self, s, s1):
        return WhereCriteria('between', (s, s1), self)
    
    def not_like(self, s):
        return WhereCriteria('not like', s, self)
    
    def not_in(self, s):
        return WhereCriteria('not in', s, self)
    
    def __eq__(self, s):
        return WhereCriteria('eq', s, self)
    
    def __lt__(self, s):
        return WhereCriteria('lt', s, self)
    
    def __le__(self, s):
        return WhereCriteria('le', s, self)
    
    def __gt__(self, s):
        return WhereCriteria('gt', s, self)
    
    def __ge__(self, s):
        return WhereCriteria('ge', s, self)
    
    def __ne__(self, s):
        return WhereCriteria('ne', s, self)


class XStringField(XField):
        
    def _format(self, value):
        if isinstance(value, unicode):
            return value
        
        return unicode(value)
    
class XIntField(XField):
        
    def _format(self, value):
        try:
            return int(value)
        except:
            return self.default_value
    
class XLongField(XField):
        
    def _format(self, value):
        return long(value)
    
class XFloatField(XField):
        
    def _format(self, value):
        return float(value)
    
from datetime import datetime
import time
class XDateTimeField(XField):
        
    def _format(self, value):
        if type(value) in [int, long, float]:
            return datetime.fromtimestamp(value)
        
        if type(value) == str:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        
        if type(value) == datetime:
            return value
    
        raise ValueError("unsupport type")
    
class XIdField(XIntField):
    
    def __init__(self, **kws):
        self.column = kws.get('column', 'id')
        self.can_null = False
        self.default_value = None

class XVersionField(XIntField):
    
    def __init__(self, **kws):
        self.column = kws.get('column', 'version')
        self.can_null = False
        self.default_value = 1
    
    
class XBelongsToField:
    
    def __init__(self, key, cls):
        self.key = key
        self.cls = cls
