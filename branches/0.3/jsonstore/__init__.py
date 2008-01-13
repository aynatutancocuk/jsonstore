from jsonstore.store import JSONStore
from jsonstore.backends import EntryManager
from jsonstore.operators import *


def escape(name):
    try:
        return name.replace('.', '%2E')
    except TypeError:
        return name


def flatten(obj, keys=[]):
    key = '.'.join(keys)
    if isinstance(obj, (int, float, long, basestring, Operator)):
        yield key, escape(obj)
    elif isinstance(obj, list):
        for item in obj:
            for pair in flatten(item, keys):
                yield pair
    elif isinstance(obj, dict):
        for k, v in obj.items():
            for pair in flatten(v, keys + [escape(k)]):
                yield pair
