
from .common_imports import *

class Match(object):
    @staticmethod
    def match_list(dl, dr, cmp=None):
        if len(dl) != len(dr):
            return (dl, dr, "list-len")
        for i, v in enumerate(dl):
            result = Match.match(v, dr[i], cmp=cmp)
            if result is not None:
                return result

    @staticmethod
    def match_dict(dl, dr, cmp=None):
        matched = set()
        for k, v in dl.items():
            if k not in dr:
                return (dl, dr, "key-l", k)
            result = Match.match(v, dr[k], cmp=cmp)
            if result is not None:
                return result
            matched.add(k)
        for k, v in dr.items():
            if k in matched:
                continue
            if k not in dl:
                return (dl, dr, "key-r", k)
            result = Match.match(dl[k], v, cmp=cmp)
            if result is not None:
                return result

    def match(o1, o2, cmp=lambda o1, o2: o1 == o2):
        if type(o1) is not type(o2):
            return (o1, o2, "type")
        if type(o1) is dict:
            result = Match.match_dict(o1, o2, cmp=cmp)
            if result is not None:
                return result
        elif type(o2) is list:
            result = Match.match_list(o1, o2, cmp=cmp)
            if result is not None:
                return result
        else:
            if not cmp(o1, o2):
                return (o1, o2)