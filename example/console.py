'''
Created on 2012-6-4

@author: lifei
'''
import sys
import datetime
import random
sys.path.insert(0, '..')
from xweb.config import XConfig
from xweb.orm import UnitOfWork

import logging

logger = logging.getLogger()
logger.setLevel(10)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
ch.setLevel(10)
logger.addHandler(ch)

config = {
    'db': {
        'default': {
            'driver':'mysql',   
            'user': 'ssro',
            'passwd': '517nrm',
            'host': '192.168.20.44',
            'db': 'webdb',
            'charset': 'utf8'
        },
    },
    'cache': {
        'default':'127.0.0.1:2000'
    },
          
    'idgenerator': {
        'count': 5
    }
    
}

XConfig.load(config)


unitofwork = UnitOfWork.inst()
conn = unitofwork.connection_manager.get('default')
mconn = unitofwork.connection_manager.get('mining')

cursor = conn.connect().cursor()
cursor.execute('select platform_user_id from core_user_connect where platform_app_id=1')
user_ids_set = set([str(r[0]) for r in cursor.fetchall()])
user_ids = list(user_ids_set)
cursor.close()

current_pos = 0
total_pos = len(user_ids)
all_ids = []
while True:
    uids = user_ids[current_pos:current_pos+10000]
    if not uids:
        break
    cursor = mconn.connect().cursor()
    sql='''SELECT a.`id` FROM sns_user AS a where a.uid in (%s)''' 
    in_p=', '.join(list(map(lambda x: '%s', uids)))
    sql = sql % in_p
    cursor.execute(sql, uids) 
    sids = [r[0] for r in cursor.fetchall()]

    if not sids:
        break
    
    print "sids: %s" % len(sids)
    

    sql='''
    SELECT c.uid FROM sns_user_friend AS a
    JOIN sns_user AS c ON a.`friend_id`=c.`id`
    WHERE a.`user_id` IN (%s);
    ''' 
    in_p=', '.join(list(map(lambda x: '%s', sids)))
    sql = sql % in_p
    cursor.execute(sql, sids) 
    fids = [str(r[0]) for r in cursor.fetchall()]
    all_ids += fids

    print "fids: %s" % len(fids)

    current_pos += 10000
    print "%s..." % (float(current_pos)/int(total_pos))

idset = set(all_ids)

print "%s" % len(idset)

cnt = 0
for id_ in user_ids_set:
    if id_ not in idset:
        cnt += 1

print cnt
