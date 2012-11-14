

class Field:
    
    def __init__(self, **kws):
        self.column = kws.get('column')
        self.default_value = kws.get('default_value')
        self.can_null = kws.get('can_null', True)
        
    def _format(self, value):
        raise RuntimeError("Unsupport")
    
    def format(self, value):
        
        if value is None:
            return self.default_value
        
        return self._format(value)


class StringField(Field):
        
    def _format(self, value):
        if isinstance(value, str):
            return value
        
        return str(value)
    
class IntField(Field):
        
    def _format(self, value):
        return int(value)
    
class LongField(Field):
        
    def _format(self, value):
        return long(value)
    
class FloatField(Field):
        
    def _format(self, value):
        return float(value)
    
from datetime import datetime
import time
class DateTimeField(Field):
        
    def _format(self, value):
        if type(value) in [int, long, float]:
            return datetime.fromtimestamp(value)
        
        if type(value) == str:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        
        if type(value) == datetime:
            return value
    
        raise ValueError("unsupport type")
    
    
class BelongsToField:
    pass