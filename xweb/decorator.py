'''
'''
from xweb.mvc import XController
from xweb.orm import Entity
from xweb.orm import XField, XBelongsToField
from xweb.mvc import XApplication

def register(cls):
    
    if issubclass(cls, XController):
        cls_name = cls.__name__
        if not cls_name.endswith("Controller"):
            return cls
        
        attr_keys = dir(cls)
        for attr_key in attr_keys:
            if attr_key.startswith('do') and attr_key.lower() != attr_key and attr_key.lower() not in attr_keys:
                attr_value = getattr(cls, attr_key)
                if callable(attr_value):
                    setattr(cls, attr_key.lower(), attr_value)
                    
        XApplication.CONTROLLERS[cls_name] = cls
                    
    elif issubclass(cls, Entity):
    
        attrs_names = dir(cls)
        fields = {}
        belongs_to_fields = {}
        for attr_name in attrs_names:
            attr_value = getattr(cls, attr_name)
            if isinstance(attr_value, XField):
                fields[attr_name] = attr_value
                if not attr_value.column:
                    attr_value.column = attr_name
                    
                attr_value.cls = cls
                
            elif isinstance(attr_value, XBelongsToField):
                belongs_to_fields[attr_name] = attr_value
                
        cls._fields = fields
        cls._belongs_to_fields = belongs_to_fields
        
        

    return cls