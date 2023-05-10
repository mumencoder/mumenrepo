
from .common_imports import *
from .Prefix import *

class Environment(object):
    def __init__(self, parent=None):
        self.properties = {}
        self.parent = parent
        self.attr = Prefix(self, "")

    def parent_chain(self):
        cnode = self
        while cnode is not None:
            yield cnode
            cnode = cnode.parent

    def prefix(self, path):
        return Prefix(self, path)

    def root(self):
        while self.parent is not None:
            self = self.parent
        return self

    def local_properties(self):
        for prop in self.properties:
            yield prop

    def unique_properties(self):
        seen = set()
        for env in self.parent_chain():
            for prop in env.properties:
                if prop in seen:
                    continue
                seen.add(prop)
                yield prop

    def filter_properties(self, re_filter):
        re_filter = re_filter.replace(".", "\.")
        re_filter = re_filter.replace("*", ".*")
        pattern = re.compile(re_filter)
        for prop in self.unique_properties():
            if pattern.fullmatch(prop):
                yield prop

    def __iter__(self):
        for prop in self.unique_properties():
            yield prop, self.get_attr(prop)

    def zip_with_dict(self, d, assign_fn=None, prefix=None):
        if prefix is None:
            prefix = self.attr
        for k, v in d.items():
            if type(v) is dict:
                prefix = getattr(prefix, k)
                if type(prefix) is not Prefix:
                    raise Exception(prefix, k)
                self.zip_with_dict(v, assign_fn=assign_fn, prefix=getattr(prefix, k) )
            else:
                assign_fn(prefix, k, v)

    def rebase(self, old_base, new_base, prop, new_env=None, copy=False):
        if prop.startswith(old_base):
            oldv = self.get_attr(prop)
            if copy is False:
                self.del_attr(prop)
            new_prop = new_base + prop[len(old_base):]
            if new_env is None:
                new_env = self
            new_env.set_attr(new_prop, oldv)
        else:
            raise Exception("prop is not prefixed by old_base")

    def set_attr(self, path, value):
        self.properties[path] = value

    def get_attr(self, path, local=False, default=None):
        if local is True:
            return self.properties[path]
        while path not in self.properties:
            self = self.parent
            if self is None:
                return default
        return self.properties[path]

    def del_attr(self, path, local=False):
        if local is True:
            del self.properties[path]
        while path not in self.properties:
            self = self.parent
            if self is None:
                raise Exception("property not found")
        del self.properties[path]
    
    def has_attr(self, path, local=False):
        if local is True:
            return path in self.properties
        while path not in self.properties:
            self = self.parent
            if self is None:
                return False
        return True

    def get(self, path, default=None):
        if self.has_attr(path):
            return self.get_attr(path)
        else:
            return default

    def get_dict(self, path):
        d = {}
        for cnode in self.parent_chain():
            if path not in cnode.properties:
                continue
            if type(cnode.properties[path]) is not dict:
                continue
            d.update(cnode.properties[path])
        return d
    
    def copy(self):
        nnode = Environment()
        for node in reversed(list(self.parent_chain())):
            nnode.properties.update( node.properties )
        return nnode
    
    def merge(self, config, inplace=False):
        if inplace:
            new_env = self
        else:
            new_env = self.branch()
        for parent in reversed(list(config.parent_chain())):
            new_env.properties.update(parent.properties)
        return new_env

    def branch(self):
        env = Environment()
        env.parent = self
        return env