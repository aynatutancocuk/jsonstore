import os
import itertools
import operator
from datetime import datetime
import time
import re
import threading
LOCAL = threading.local()

try:
    import sqlite3 as sqlite
except ImportError:
    from pysqlite2 import dbapi2 as sqlite

from shove import Shove
from uuid import uuid4

from jsonstore.operators import Operator, Equal


# http://lists.initd.org/pipermail/pysqlite/2005-November/000253.html
def regexp(expr, item):
    p = re.compile(expr)
    return p.match(item) is not None


class EntryManager(object):
    def __init__(self, store='simple://', cache='simple://', index='index.db', **kwargs):
        self.store = Shove(store, cache, **kwargs)

        self.index = index
        if not os.path.exists(self.index):
            self._create_table()
            self.reindex()

    # Thread-safe connection manager. Conections are stored in the 
    # ``threading.local`` object, so they can be safely reused in the
    # same thread.
    @property
    def conn(self):
        if not hasattr(LOCAL, 'conns'):
            LOCAL.conns = {}

        if self.index not in LOCAL.conns:
            LOCAL.conns[self.index] = sqlite.connect(self.index, 
                    detect_types=sqlite.PARSE_DECLTYPES|sqlite.PARSE_COLNAMES)
        LOCAL.conns[self.index].create_function("regexp", 2, regexp)
        return LOCAL.conns[self.index]

    def _create_table(self):
        self.conn.executescript("""
            CREATE TABLE flat (
                id VARCHAR(255),
                updated timestamp,
                position CHAR(255),
                leaf NUMERIC);
            CREATE INDEX position ON flat (position);
        """)
        self.conn.commit()

    def create(self, entry=None, **kwargs):
        if entry is None:
            entry = kwargs
        else:
            assert isinstance(entry, dict), "Entry must be instance of ``dict``!"
            entry.update(kwargs)

        # __id__ and __updated__ can be overriden.
        id_ = entry.setdefault('__id__', str(uuid4()))
        updated = entry.setdefault('__updated__', datetime.utcnow())
        if not isinstance(updated, datetime):
            updated = datetime(
                *(time.strptime(updated, '%Y-%m-%dT%H:%M:%SZ')[0:6]))

        # Store entry.
        self.store[id_] = entry
        self.index_entry(entry)
        return entry

    def delete(self, key):
        del self.store[key]

        self.conn.execute("""
            DELETE FROM flat
            WHERE id=?;
        """, (key,))
        self.conn.commit()

    def update(self, entry=None, **kwargs): 
        if entry is None:
            entry = kwargs
        else:
            assert isinstance(entry, dict), "Entry must be instance of ``dict``!"
            entry.update(kwargs)

        id_ = entry['__id__']
        self.delete(id_)
        return self.create(entry)

    def search(self, obj=None, size=None, offset=0, count=False, **kwargs):
        """
        Search database using a JSON object.
        
        The idea is here is to flatten the JSON object (the "key"),
        and search the index table for each leaf of the key using
        an OR. We then get those ids where the number of results
        is equal to the number of leaves in the key, since these
        objects match the whole key.
        
        """
        if obj is None:
            obj = kwargs
        else:
            assert isinstance(obj, dict), "Search key must be instance of ``dict``!"
            obj.update(kwargs)

        # Check for id.
        id_ = obj.pop('__id__', None)

        # Flatten the JSON key object.
        pairs = list(flatten(obj))
        pairs.sort()
        groups = itertools.groupby(pairs, operator.itemgetter(0))

        query = ["SELECT DISTINCT id FROM flat"]
        condition = []
        params = []

        # Check groups from groupby, they should be joined within
        # using an OR.
        leaves = 0
        for (key, group) in groups:
            group = list(group)
            subquery = []
            for position, leaf in group:
                params.append(position)
                if not isinstance(leaf, Operator):
                    leaf = Equal(leaf)
                subquery.append("(position=? AND leaf %s)" % leaf)
                params.extend(leaf.params)
                leaves += 1

            condition.append(' OR '.join(subquery))

        # Build query.
        if condition or id_ is not None:
            query.append("WHERE")
        if id_ is not None:
            query.append("id=?")
            params.insert(0, id_)
            if condition:
                query.append("AND")
        if condition:
            # Join all conditions with an OR.
            query.append("(%s)" % " OR ".join(condition))
        if leaves:
            query.append("GROUP BY id HAVING COUNT(*)=%d" % leaves)
        query.append("ORDER BY updated DESC")
        if size is not None:
            query.append("LIMIT %s" % size)
        if offset:
            query.append("OFFSET %s" % offset)
        query = ' '.join(query)

        if count:
            curs = self.conn.execute("SELECT COUNT(*) FROM (%s) AS ITEMS"
                    % query, tuple(params))
            return curs.fetchone()[0]
        else:
            curs = self.conn.execute(query, tuple(params))
            return [self.store[row[0]] for row in curs]

    def index_entry(self, entry):
        # Index entry.
        indexes = [(entry['__id__'], entry['__updated__'], k, v)
                for (k, v) in flatten(entry) if k != '__id__']
        self.conn.executemany("""
            INSERT INTO flat (id, updated, position, leaf)
            VALUES (?, ?, ?, ?);
        """, indexes)
        self.conn.commit()

    def reindex(self):
        self.conn.execute("DELETE FROM flat;")
        self.conn.commit()
        for entry in self.store:
            self.index_entry(self.store[entry])
        
    def close(self):
        self.conn.close()
        del LOCAL.conns[self.index]


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
