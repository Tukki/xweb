

class XConfig:
    config = {}
    
    @classmethod
    def load(cls, conf):
        cls.config.update(conf)
    
    @classmethod
    def get(cls, key, value=None):
        return cls.config.get(key, value)
    
    
