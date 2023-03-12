
from .common_imports import *
from .Prefix import *

class Environment(object):
    def __init__(self, parent=None):
        self.properties = {}
        self.event_handlers = {}
        self.parent = parent
        self.name = ""
        self.attr = Prefix(self, "")

    def parent_chain(self):
        cnode = self
        while cnode is not None:
            yield cnode
            cnode = cnode.parent

    def event_defined(self, event_name):
        for cnode in self.parent_chain():
            if event_name in cnode.event_handlers:
                return True
        return False

    async def send_event(self, event_name, *args, **kwargs):
        for cnode in self.parent_chain():
            if event_name in cnode.event_handlers:
                await cnode.event_handlers[event_name](*args, **kwargs)
            
    def get_dict(self, path):
        d = {}
        for cnode in self.parent_chain():
            if path not in cnode.properties:
                continue
            if type(cnode.properties[path]) is not dict:
                continue
            d.update(cnode.properties[path])
        return d

    def prefix(self, path):
        return Prefix(self, path)

    def get_list(self, value):
        l = []
        for cnode in self.parent_chain():
            if value not in cnode.properties:
                continue
            l.append(cnode[value])
        return l

    def copy(self):
        nnode = Environment()
        for node in reversed(list(self.parent_chain())):
            nnode.properties.update( node.properties )
            nnode.event_handlers.update( node.event_handlers )
        return nnode

    def fullname(self):
        if self.parent is not None:
            return self.parent.fullname() + "/" + self.name 
        else:
            return self.name

    def root(self):
        while self.parent is not None:
            self = self.parent
        return self

    def parse_path(self, path):
        node = ""
        for c in path:
            if c == "/" or c == "." or c == ":":
                if node != "":
                    yield node
                    node = ""
                yield c
            else:
                node += c
        if node != "":
            yield node

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

    def __iter__(self):
        for prop in self.unique_properties():
            yield prop, self.get_attr(prop)

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

    def filter_properties(self, re_filter):
        re_filter = re_filter.replace(".", "\.")
        re_filter = re_filter.replace("*", ".*")
        pattern = re.compile(re_filter)
        for prop in self.unique_properties():
            if pattern.fullmatch(prop):
                yield prop

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
    
    def attr_exists(self, path, local=False):
        if local is True:
            return path in self.properties
        while path not in self.properties:
            self = self.parent
            if self is None:
                return False
        return True

    def get(self, path, default=None):
        if self.attr_exists(path):
            return self.get_attr(path)
        else:
            return default

    def merge(self, config, inplace=False):
        if inplace:
            new_env = self
        else:
            new_env = self.branch()
        for parent in reversed(list(config.parent_chain())):
            new_env.properties.update(parent.properties)
            new_env.event_handlers.update(parent.event_handlers)
        return new_env

    def branch(self):
        env = Environment()
        env.parent = self
        return env