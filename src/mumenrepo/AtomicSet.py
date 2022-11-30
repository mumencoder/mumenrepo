
from .common_imports import *

class AtomicSet(object):
    def __init__(self):
        self.lock = asyncio.Lock()
        self.s = set()

    async def check_add(self, key):
        async with self.lock:
            rval = None
            if key in self.s:
                rval = True
            else:
                self.s.add(key)
                rval = False
            return rval