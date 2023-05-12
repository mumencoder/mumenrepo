
from .common_imports import *
class EventManager(object):
    def __init__(self):
        self.sinks = {}
        self.sinks_by_event = collections.defaultdict(set)
        self.sinks_by_id = collections.defaultdict(set)

    def add_sink(self, event_name, sink_id, fn):
        k = (event_name, sink_id)
        if k in self.sinks:
            raise Exception(k, "exists")
    
        self.sinks[k] = fn
        self.sinks_by_event[event_name].add( k )
        self.sinks_by_id[sink_id].add( k )

    async def send_event(self, event_name, *args, **kwargs):
        for k in self.sinks_by_event[event_name]:
            await self.sinks[k](*args, **kwargs)