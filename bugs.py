from kairos import Timeseries
import redis
import time
import datetime
import pprint
import random

KEY = 'example.com'
KEY_PREFIX = 'timedata:domain'

client = redis.Redis('localhost', 6379)
minute_count = Timeseries(client, {
        'minute':{
            'step':60,              # 60 seconds
            'steps':15,             # last 15 minutes
            #'read_cast' : float,   # cast all results as floats
            'count_only' : True,    # store counts only.
        }
    }, key_prefix=KEY_PREFIX)

def hit(domain):
    print "hit: %s @ %d" % (domain, time.time())
    minute_count.insert(domain, 1)

def monitor():
    while True:
        get = minute_count.get(KEY, 'minute')
        series = minute_count.series(KEY, 'minute')
        count = minute_count.count(KEY, 'minute')
        last_5_condensed = minute_count.series(KEY, 'minute', steps=5, condensed=True)
        print get, last_5_condensed
        time.sleep(1)

monitor()
