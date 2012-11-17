

class XField:
    
    def __init__(self, **kws):
        self.column = kws.get('column')
        self.default_value = kws.get('default')
        self.can_null = kws.get('null', True)
        
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
