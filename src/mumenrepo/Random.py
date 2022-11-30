
from .common_imports import *

class Random(object):
    @staticmethod 
    def generate_string(n):
        return "".join([random.choice(string.ascii_lowercase + string.ascii_uppercase) for i in range(0,n)])

    @staticmethod
    def to_choices(d):
        return { "values":list(d.keys()), "weights":list(d.values()) }

    @staticmethod
    def choose_choices(d, k):
        return random.choices(d['values'], weights=d['weights'], k=k)