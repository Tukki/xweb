from orm.entity import Entity


class Address(Entity):
    
    _table_name = 'user'
    
    _keys = ['name', 'passwd', 'create_time']


class User(Entity):
    
    _keys = ['name', 'passwd', 'create_time', 'address_id']
    
    _belongs_to = {'address': ('address_id', Address)}