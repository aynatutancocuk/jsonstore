from datetime import datetime

from jsonstore.store import JSONStore
from jsonstore.backends import EntryManager
from jsonstore.operators import *


def escape(name):
    try:
        return name.replace('.', '%2E')
    except TypeError:
        return name


def datetime_to_iso(obj):
    try:
        return obj.isoformat().split('.', 1)[0] + 'Z'
    except:
        return obj


def flatten(obj, keys=[]):
    key = '.'.join(keys)
    if isinstance(obj, list):
        for item in obj:
            for pair in flatten(item, keys):
                yield pair
    elif isinstance(obj, dict):
        for k, v in obj.items():
            for pair in flatten(v, keys + [escape(k)]):
                yield pair
    elif isinstance(obj, datetime):
        yield key, datetime_to_iso(obj)
    elif isinstance(obj, Operator):
        obj.params = [datetime_to_iso(p) for p in obj.params]
        yield key, obj
    else:
        yield key, obj
