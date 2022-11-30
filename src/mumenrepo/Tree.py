
from .common_imports import *

class Tree(object):
    def __init__(self):
        self.branches = {}
        self.segment = None

    def get_branch(self, path):
        trunk = self
        for segment in path:
            if segment not in trunk.branches:
                trunk = Tree()
                trunk.segment = segment
                trunk.branches[segment] = trunk
            else:
                trunk = trunk.branches[segment]
        return trunk

    def dfs_visit_all(self):
        yield self
        for branch in self.branches.values():
            yield from branch.dfs_visit_all()