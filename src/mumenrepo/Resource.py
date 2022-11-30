
from .common_imports import *

class Resource(object):
    @staticmethod
    async def with_resource(env, resource, action):
        while True:
            result = await resource.acquire()
            if result is not None:
                env.attr.resource.result = result["data"]
                break
            await asyncio.sleep(0.1)
        try:        
            await action(env)
        finally:
            resource.release(resource)

    class Tracker(object):
        def __init__(self, limit=None):
            self.limit = limit
            self.resources = {}
            self.lock = asyncio.Lock()
            
        def get_resource_data(self, i):
            raise NotImplemented()

        def ensure_exist(self, data):
            raise NotImplemented()

        async def acquire(self):
            async with self.lock:
                i = 0
                while True:
                    resource = self.get_resource(i)
                    if resource is None:
                        return None
                    if resource['available'] is True:
                        resource['available'] = False
                        return resource
                    i += 1

        def release(self, resource):
            resource['available'] = True

        def get_resource(self, i):
            if i >= self.limit:
                return None

            if i not in self.resources:
                data = self.get_resource_data(i)
                self.ensure_exist(data)
                self.resources[i] = {'available':True, 'data':data}

            return self.resources[i]

    class Counted(object):
        def __init__(self, amount):
            self.amount = amount
            self.counts = 0
        
        async def acquire(self):
            while self.counts >= self.amount:
                await asyncio.sleep(0.1)
            self.counts += 1

        def release(self, res):
            self.counts -= 1

        def get_usage(self):
            return self.counts
            
    class Pooled(object):
        def __init__(self, o):
            self.o = o