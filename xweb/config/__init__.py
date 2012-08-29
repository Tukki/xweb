

class XConfig:
    config = {}
    
    @classmethod
    def load(cls, conf):
        cls.config.update(conf)

    @classmethod
    def get(cls, key, value=None):
        keys = key.split(".")
        
        c = cls.config
        for k in keys:
            c = c.get(k)
            
            if c is None:
                return value
            
        return c or value