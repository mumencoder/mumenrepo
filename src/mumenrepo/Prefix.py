
from .common_imports import *

class Prefix(object):
    def __init__(self, root, path):
        object.__setattr__(self, 'root', root)
        object.__setattr__(self, 'path', path)

    def __getattribute__(self, attr):
        cnode = object.__getattribute__(self, 'root')
        path = object.__getattribute__(self,'path') + "." + attr
        while path not in cnode.properties:
            cnode = cnode.parent
            if cnode is None:
                return Prefix(object.__getattribute__(self, 'root'), path)
        return cnode.properties[path]

    def __hasattribute__(self, attr):
        cnode = object.__getattribute__(self, 'root')
        path = object.__getattribute__(self,'path') + "." + attr
        while path not in cnode.properties:
            cnode = cnode.parent
            if cnode is None:
                return False
        return True

    def __setattr__(self, attr, value):
        cnode = object.__getattribute__(self, 'root')
        path = object.__getattribute__(self, 'path') + "." + attr
        cnode.properties[path] = value

    def __delattr__(self, attr):
        cnode = object.__getattribute__(self, 'root')
        path = object.__getattribute__(self, 'path') + "." + attr
        del cnode.properties[path]

    def __repr__(self):
        return f"<PREFIX {object.__getattribute__(self,'path')}>"