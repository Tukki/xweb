

class Criteria:
    
    def __init__(self, t, data=[], field=None):
        self.type = t
        self.data = data
        self.field = field
        
    def filter(self, *args):
        self.data += args
        return self
        
def or_(*args):
    return Criteria('or', args)

def and_(*args):
    return Criteria('and', args)

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
        return Criteria('like', s, self)
    
    def in_(self, s):
        return Criteria('in', s, self)
    
    def between(self, s, s1):
        return Criteria('between', (s, s1), self)
    
    def not_like(self, s):
        return Criteria('not like', s, self)
    
    def not_in(self, s):
        return Criteria('not in', s, self)
    
    def __eq__(self, s):
        return Criteria('eq', s, self)
    
    def __lt__(self, s):
        return Criteria('lt', s, self)
    
    def __le__(self, s):
        return Criteria('le', s, self)
    
    def __gt__(self, s):
        return Criteria('gt', s, self)
    
    def __ge__(self, s):
        return Criteria('ge', s, self)
    
    def __ne__(self, s):
        return Criteria('ne', s, self)


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
