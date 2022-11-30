
from .common_imports import *

from .Prefix import *

class Json(object):
    class BetterEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, pathlib.PurePath):
                return str(obj)
            if isinstance(obj, Prefix):
                raise Exception(f"cannot serialize prefix {obj}")
            if isinstance(obj, dict):
                for k,v in obj.items():
                    if type(k) is Prefix:
                        raise Exception(f"cannot serialize prefix {obj}")
            return json.JSONEncoder.default(self, obj)