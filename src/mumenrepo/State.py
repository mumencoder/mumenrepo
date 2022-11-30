
from .common_imports import *
from .File import *

class State(object):
    class Filesystem(object):
        def __init__(self, path, mode="", loader=lambda o: o, saver=lambda o: o):
            self.path = path
            self.mode = mode

            self.loader = loader
            self.saver = saver

        def get(self, key, default=None):
            if not os.path.exists(self.path / key):
                return default
            
            with File.open(self.path / key, "r" + self.mode) as f:
                result = f.read()
                if len(result) == 0:
                    return default
                    
            return self.loader( result )

        def set(self, key, value):
            with File.open(self.path / key, "w" + self.mode) as f:
                f.write( self.saver(value) )

        def rm(self, key):
            try:
                os.remove( self.path / key )
            except OSError:
                pass

        def reset(self, key):
            if not os.path.exists(self.path / key):
                return
            else:
                os.remove( self.path / key )