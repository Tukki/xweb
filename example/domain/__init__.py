from xweb.orm import Entity
from xweb.orm import MultiIdEntity

class Category(Entity):
    '''
    classdocs
    '''
    
    _keys = ['name']
    
    
class StopTime(MultiIdEntity):
    
    _table_name = 'basic_stoptimes'
    
    _primary_key = ('train_code', 'station_no')
    
    _keys = ['train_name', 'train_code', 'station_no', 'station_name', 'arrive_time',
             'start_time', 'cost_time', 'cost_day', 'distance']

class Video(Entity):
    
    _table_name = 'video'
    
    _keys = ['title', 'category_id', 'source', 'mp4_url', 
             'm3u8_url', 'swf_url', 'digg_count', 
             'bury_count', 'comment_count']
    
    _default_values = {'digg_count': 0, 'bury_count': 0, 'comment_count': 0}
    
    _belongs_to = {'category': ('category_id', Category),
        'stoptime': (('title', 'digg_count'), StopTime)}
    