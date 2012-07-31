#!/usr/bin/env python
"""This is intended to serve as an example of using Kairos to generate and
display time series histogram data for an event.
"""
from kairos import Timeseries
import redis
import time
import datetime
import random
from argparse import ArgumentError

MAX_WIDTH_COLUMNS = 60

class EventCounter(object):
    """Manage event counters."""
    def __init__(self, redis_client, key_prefix):
        """Create our counter structure."""
        if not key_prefix:
            raise ValueError('key_prefix must be provided and length must be >0')
        
        self.counters = Timeseries(redis_client, {
                'minute': {
                        'step': 60,              # 60 seconds
                        'steps': 60,             # last hour
                        'count_only' : True,    # store counts only.
                    },
                'hour': {
                        'step': 3600,           # Hourly
                        'steps': 24,            # Last day
                        'count_only' : True,    # Store counts only.
                    },
                'daily': {
                        'step': 86400,          # Daily
                        'steps': 30,            # Last 30 days
                        'count_only': True,     # Store counts only.
                    },
            }, 
            key_prefix=key_prefix)
        self.key_prefix = key_prefix
        self.redis_client = redis_client

    def record_hit(self, item_id):
        """Record a hit.  All this does is increments the current time bucket."""
        self.counters.insert(item_id, 1)
    
    def get_counts(self, interval_name, item_id, n_recent_periods):
        """
        Return the n most recent periods for a given interval and item_id as a list.
        Items are returned oldest first; most recent entry is last in list.
        """
        series = self.counters.series(item_id, interval_name, steps=n_recent_periods, condensed=False)
        return series.values()
    
    def get_sum(self, interval_name, item_id, n_recent_periods):
        """Return the sum of the counts for the most recent periods."""
        return sum(self.get_counts(interval_name, item_id, n_recent_periods))
    
    def delete_keys(self):
        """Clean up (delete) all keys used by this instance."""
        raise NotImplementedError() 
    
    
KEY = 'example.com'
KEY_PREFIX = 'timedata:domain'
client = redis.Redis('localhost', 6379)
counters = EventCounter(redis_client=client, key_prefix=KEY_PREFIX)

def hit(domain):
    print "hit: %s @ %d" % (domain, time.time())
    counters.record_hit(domain)

def dump_series(base_time, series):
    for ts, value in series.iteritems():
        print "%02d(%02d)" % ((ts-base_time)/60, value), 
    print
    
def plot_series(series, max_val, limit=15):
    scale = max_val / MAX_WIDTH_COLUMNS
    # Series is in oldest to latest order (oldest first).
    # 
    offset = 1-limit
    for count in series[-limit:]:
        print "%4d (%03d): %s" % (offset, count, "*" * (count/scale))
        offset += 1

def sum_series(series):
    # series to list: series.list()
    return sum(series.values())

def generate():
    # Clear any existing keys.
    try:
        counters.delete_keys()
    except NotImplementedError:
        print "EventCounter.delete_keys not implemented, ignoring."
        
    # record a couple of hits.
    hit(KEY)
    hit(KEY)
    
    start = datetime.datetime.now()
    x = 0
    while True:
        time.sleep(1)
        # Record a hit every once in a while (approx. every 3.5 seconds...)
        if x % random.randint(2,5) == 0:
            hit(KEY)
        x += 1

interval_max_values = { 'minute' : 100, 'hour': 2000, 'daily': 2000*24 }

def monitor(interval_name, limit=5):
    while True:
        series = counters.get_counts(interval_name, KEY, limit)
        sum = counters.get_sum(interval_name, KEY, 5)
        #series = counters.series(KEY, interval_name)
        #last_5 = counters.series(KEY, interval_name, steps=5, condensed=False)
        # sum = sum_series(last_5)
        # This should work but breaks: condensed = counters.series(KEY, interval_name, steps=5, condensed=True)
        #dump_series(time.time(), series)
        plot_series(series, interval_max_values[interval_name], limit=limit)
        print "%d in last %d %s (~%2.2f per %s)." % (sum, limit, interval_name, sum/5.0, interval_name)
        time.sleep(1)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Test something.')
    parser.add_argument('op', metavar='op', help='If op=generate, generates random data.  If op=monitor, monitors generated data.', default='generate', action="store", choices=['generate', 'monitor'])
    parser.add_argument('-i', '--interval', metavar='interval', default='minute', action='store', choices=['minute', 'hour', 'daily'])
    parser.add_argument('-l', '--limit', metavar='limit', default=15, action='store', type=int, help='The number of past entries to display in histogram in monitor mode.')
    opts = parser.parse_args()
    if opts.op == 'generate':
        generate()
    else:
        monitor(opts.interval, opts.limit)
