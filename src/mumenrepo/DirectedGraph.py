
from .common_imports import *

class DirectedGraph(object):
    def __init__(self):
        self.forward_links = collections.defaultdict(list)
        self.back_links = collections.defaultdict(list)
        self.sorted_nodes = collections.defaultdict(list)
        self.orders = {}

    def assign_order(self, node, order):
        if node in self.orders:
            raise Exception("node already assigned to graph")
        else:
            self.orders[node] = order
            self.sorted_nodes[order].append( node )

    def add_root(self, root):
        self.assign_order(root, 1)

    def forward_nodes(self, node):
        for fnode in self.forward_links[node]:
            yield fnode
            yield from self.forward_nodes(fnode)

    def link(self, before, after):
        if before not in self.orders:
            raise Exception("before node not assigned to graph")

        if after not in self.orders:
            self.assign_order(after, self.orders[before]+1)

        if self.orders[after] <= self.orders[before]:
            raise Exception("cycle detected")

        self.forward_links[before].append( after )
        self.back_links[after].append( before )

    def stringify(self):
        s = ""
        for before, afters in self.forward_links.items():
            s += f"{before} -> {' '.join([str(after) for after in afters])}\n"
        return s