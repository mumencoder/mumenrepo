
from .common_imports import *

class Object(object):
    def walk_attrs(obj):
        if hasattr(obj, '__dict__'):
            for k, v in vars(obj).items():
                yield k, v
                for k, v in Object.walk_attrs(v):
                    yield k, v

    def add_dict(self, d):
        for k, v in d.items():
            setattr(self, k, v)

    def import_file(path):
        with open(path, "rb") as f: 
            global_config = {}
            exec(compile(f.read(), path, mode="exec"), global_config)
            obj = Object()
            obj.add_dict(global_config)
        return obj