import urllib

from jsonstore.store import JSONStore
from jsonstore.backends import EntryManager
from jsonstore.operators import *


def quote_(name):
    try:
        return urllib.quote(name).replace('.', '%2E')
    except TypeError:
        return name


def flatten(obj, keys=[]):
    key = '.'.join(keys)
    if isinstance(obj, (int, float, long, basestring, Operator)):
        yield key, quote_(obj)
    elif isinstance(obj, list):
        for item in obj:
            for pair in flatten(item, keys):
                yield pair
    elif isinstance(obj, dict):
        for k, v in obj.items():
            for pair in flatten(v, keys + [quote_(k)]):
                yield pair
