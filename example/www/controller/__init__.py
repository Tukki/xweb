from xweb.mvc.controller import *
from xweb.config import XConfig
from werkzeug.exceptions import NotFound, HTTPException #@UnresolvedImport
from xweb.mvc.web import XResponse

from domain import Video, StopTime


class DefaultController(XController):

    @settings(mimetype='xml')
    def doIndex(self):
        
        print UnitOfWork.inst().connection_manager.get().fetchRow('''
        SELECT train_code,station_no,train_name,train_code,station_no,station_name,arrive_time,start_time,cost_time,cost_day,distance 
FROM `basic_stoptimes` 
WHERE `train_code`='01000000Z202' AND `station_no`=1 LIMIT 1;
        ''')
        print UnitOfWork.inst().connection_manager.get().fetchRow('''
        SELECT train_code,station_no,train_name,train_code,station_no,station_name,arrive_time,start_time,cost_time,cost_day,distance 
FROM `basic_stoptimes` 
WHERE `train_code`=%s AND `station_no`=1 LIMIT 1;
        ''', '01000000Z202')
        
        
        import time
        
        self.context['stops'] = StopTime.getListByCond('1=1 limit 10')
        
        video = Video.getListByCond()[0]
        video.title = time.time()
        print video.stoptime
        

        '''
        self.echo("hehe")
        import time
        self.context['user'] = time.time()
        
        for i in range(1000):
            self.secure_cookies[i] = i*i 

        self.context['link'] = self.createUrl('default/long', short_id=110000L)
        
        s = StopTime.get(train_code='01000000Z202', station_no=1)
        s.distance = 0
        
        video = Video.getListByCond()[0]
        video.title = time.time()
        print video.category
        print video.stoptime
        
        self.context['stops'] = StopTime.getListByCond('1=1 limit 10')
        '''
       
    def doHelp(self):
        self.echo("hello world")
        
        
    @settings(mimetype='text')
    def doShort(self):
        self.echo("<a href=%s>hehe</a>" % self.createUrl('default/short', short_id=110000L))
        self.mimetype = 'text/xhtml'
        
    @settings(status_code=500)
    def handleException(self, **kwargs):
        ex = kwargs.get('ex')
        assert isinstance(ex, Exception)
        self.response.data = str(ex)
        
        if self.app.use_debuger:
            raise
