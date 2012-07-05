'''
Created on 2012-6-8

@author: lifei
'''

import threading

class IdGenerator:
    def __init__(self, engine=None, fetch_count=5):
        self._cache_ids = None
        self._fetch_count = fetch_count
        self._lock = threading.Lock()
        self._engine = engine

    def _fetch_ids(self):
        connection = self._engine.connect().cursor()
        connection.execute(
                "update idgenerator set next_id=LAST_INSERT_ID(next_id+%s)" % self._fetch_count)
        connection.execute("select LAST_INSERT_ID() as next_id")
        next_id = connection.fetchone()[0]
        connection.close()
        return range(next_id-self._fetch_count, next_id)
                

    def get(self):
        with self._lock:
            if not self._cache_ids:
                self._cache_ids = self._fetch_ids()
            return self._cache_ids.pop(0)