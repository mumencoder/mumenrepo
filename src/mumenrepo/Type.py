
from .common_imports import *

class Type:
    def iter_types(obj):
        if type(obj) is type:
            yield obj
            for sobj in obj.__dict__.values():
                yield from Type.iter_types(sobj)

    def mix_types(base, mixin):
        if type(base) is type:
            yield (base, mixin)
            for key, sbase in dict(base.__dict__).items():
                if key in mixin.__dict__:
                    yield from Type.mix_types(sbase, mixin.__dict__[key])

    def mix_fn(base, mixin, fn_name):
        for base_ty, mixin_ty in Type.mix_types(base, mixin):
            if hasattr(mixin_ty, fn_name):
                setattr(base_ty, fn_name, getattr(mixin_ty, fn_name) )