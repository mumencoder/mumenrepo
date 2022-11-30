
from .common_imports import *

class HCL(object):
    current_hcl = None

    class Ctx(object):
        def __enter__(self):
            HCL.current_hcl.ctx_stack.append( HCL.current_hcl.current_ctx )
            HCL.current_hcl.current_ctx = self

        def __exit__(self, *args):
            HCL.current_hcl.current_ctx = HCL.current_hcl.ctx_stack[-1]
            HCL.current_hcl.ctx_stack.pop()

    class Textify(object):
        def __init__(self):
            self.indent = 0
            self.out = ""
            self.new_line = True

        def write(self, s):
            self.out += s
            self.new_line = False

        def begin_line(self):
            self.out += "\n"
            self.out += self.indent * "  "
            self.new_line = True

        def begin_scope(self):
            self.indent += 1
            self.write(" {")
            self.begin_line()

        def end_scope(self):
            self.indent -= 1
            self.begin_line()
            self.write("}")

    class Block(Ctx):
        def __init__(self, *labels):
            self.labels = labels
            self.nodes = []

        def add_child(self, node):
            self.nodes.append( node )

        def to_hcl(self, hcl):
            if len(self.labels) < 1:
                raise Exception("unlabeled block", self)
            hcl.write( f"{self.labels[0]} " )
            for label in self.labels[1:]:
                if type(label) is not str:
                    raise Exception("invalid label", label, self)
                hcl.write( f' "{label}"')

            hcl.begin_scope()
            for node in self.nodes:
                node.to_hcl( hcl )
            hcl.end_scope()
            hcl.begin_line()

    class RootBlock(Block):
        def __init__(self):
            super().__init__([])

        def to_hcl(self):
            hcl = HCL.HCLOutput()
            for node in self.nodes:
                node.to_hcl( hcl )
            return hcl.out

    class List(Ctx):
        def __init__(self, *values):
            self.nodes = values

        def add_child(self, node):
            self.nodes.append( node )

        def to_hcl(self, hcl):
            hcl.write( '[' )
            for o in self.nodes[0:-1]:
                HCL.convert_object(hcl, o)
                hcl.write(",")
            if len(self.nodes) > 0:
                HCL.convert_object(hcl, self.nodes[-1])
            hcl.write( ']' )

    class Property(Ctx):
        def __init__(self, key, value):
            self.key = key
            self.value = value

        def add_child(self, value):
            self.value = value
            
        def to_hcl(self, hcl):
            hcl.write( f'{self.key} = ')
            HCL.convert_object(hcl, self.value)
            hcl.begin_line()

    class Object(Ctx):
        def __init__(self, o):
            self.o = o

        def add_child(self, prop):
            self.o[prop.key] = prop.value

        def to_hcl(self, hcl):
            hcl.begin_scope()
            for k, v in self.o.items():
                hcl.begin_line()
                hcl.write( f'"{k}" = ' )
                HCL.convert_object(hcl, v)
            hcl.end_scope()

    class Expression(Ctx):
        def __init__(self, expr):
            self.expr = expr

        def to_hcl(self, hcl):
            hcl.write( self.expr )

    @staticmethod
    def convert_object(hcl, o):
        if isinstance(o, HCL.Object):
            return o.to_hcl(hcl)
        elif isinstance(o, HCL.Expression):
            return o.to_hcl(hcl)
        elif type(o) is list:
            HCL.List( *o ).to_hcl(hcl)
        elif type(o) is dict:
            HCL.Object( o ).to_hcl(hcl)
        elif type(o) in [int, float]:
            hcl.write( str(o) )
        elif type(o) is str:
            hcl.write( f'"{o}"' )
        elif type(o) is bool:
            if o is True:
                hcl.write( "true" )
            elif o is False:
                hcl.write( "false")
            else:
                raise Exception()
        else:
            raise Exception("cannot convert", o)

    def __init__(self):
        self.root = HCL.RootBlock()
        self.current_ctx = self.root
        self.ctx_stack = collections.deque()

    def __enter__(self):
        HCL.current_hcl = self

    def __exit__(self, *args):
        HCL.current_hcl = None

    def to_hcl(self):
        return self.root.to_hcl()

    def block(self, *labels):
        new_block = self.Block(*labels)
        if self.current_ctx is not None:
            self.current_ctx.add_child( new_block )
        return new_block

    def prop(self, key, value=None):
        new_prop = self.Property(key, value)
        if self.current_ctx is not None:
            self.current_ctx.add_child( new_prop )
        return new_prop

    def obj(self, **props):
        new_obj = self.Object(props)
        if self.current_ctx is not None:
            self.current_ctx.add_child( new_obj )
        return new_obj

    def tflist(self):
        new_list = self.List()
        if self.current_ctx is not None:
            self.current_ctx.add_child( new_list )
        return new_list

    def expr(self, expr):
        new_expr = self.Expression(expr)
        return new_expr

    class Json(object):
        def convert_json(j, item):
            if isinstance(item, HCL.RootBlock):
                return HCL.convert_root(j, item)
            elif isinstance(item, HCL.Block):
                return HCL.convert_block(j, item)
            elif isinstance(item, HCL.Property):
                return HCL.convert_property(j, item)
            elif isinstance(item, HCL.Object):
                return item.o
            elif isinstance(item, HCL.List):
                return HCL.convert_list(j, item)
            elif item is None:
                return None
            elif type(item) in [bool, int, float, str, list, dict]:
                return item
            else:
                raise Exception("cannot convert", item)

        def convert_root(j, block):
            for node in j.nodes:
                HCL.convert_json( j, node )
            return j

        def convert_block(j, block):
            for label in block.labels[0:-1]:
                if type(j) is not dict:
                    raise Exception("invalid json", label, j)
                if type(label) is not str:
                    raise Exception("invalid label", label, j)
                if label not in j:
                    j[label] = {}
                elif not isinstance(j[label], dict):
                    raise Exception("invalid labels on block", block.labels)
                j = j[label]

            block_json = {}
            for node in block.nodes:
                HCL.convert_json( block_json, node )
            j[block.labels[-1]] = block_json

        def convert_property( j, prop):
            j[prop.key] = HCL.convert_json( j, prop.value )

        def convert_object( j, obj):
            new_o = {}
            for k, v in obj.o.items():
                new_o[k] = HCL.convert_json( j, v )
            return new_o

        def convert_list(j, l):
            new_l = []
            for o in l.nodes:
                new_l.append( HCL.convert_object(j, o) )
            return new_l