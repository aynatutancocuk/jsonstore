import os.path
import itertools
import operator
from datetime import datetime
import time
import re
import threading
LOCAL = threading.local()

from uuid import uuid4
from simplejson import loads, dumps
from pysqlite2 import dbapi2 as sqlite

from jsonstore.operators import Operator, Equal
from jsonstore import flatten


# http://lists.initd.org/pipermail/pysqlite/2005-November/000253.html
def regexp(expr, item):
    p = re.compile(expr)
    return p.match(item) is not None


class EntryManager(object):
    def __init__(self, location):
        self.location = location
        if not os.path.exists(location):
            self._create_table()

    # Thread-safe connection manager. Conections are stored in the 
    # ``threading.local`` object, so they can be safely reused in the
    # same thread.
    @property
    def conn(self):
        if not hasattr(LOCAL, 'conns'):
            LOCAL.conns = {}

        if self.location not in LOCAL.conns:
            LOCAL.conns[self.location] = sqlite.connect(self.location, 
                    detect_types=sqlite.PARSE_DECLTYPES|sqlite.PARSE_COLNAMES)
        LOCAL.conns[self.location].create_function("regexp", 2, regexp)
        return LOCAL.conns[self.location]

    def _create_table(self):
        curs = self.conn.cursor()
        curs.executescript("""
            CREATE TABLE store (
                id VARCHAR(255) PRIMARY KEY NOT NULL,
                entry TEXT,
                updated timestamp
            );
            CREATE INDEX id ON store (id);

            CREATE TABLE flat (
                id VARCHAR(255),
                position CHAR(255),
                leaf NUMERIC
            );
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
        id_ = entry.pop('__id__', str(uuid4()))
        updated = entry.pop('__updated__',
                datetime.utcnow())
        if not isinstance(updated, datetime):
            updated = datetime(
                *(time.strptime(updated, '%Y-%m-%dT%H:%M:%SZ')[0:6]))

        # Store entry.
        curs = self.conn.cursor()
        try:
            curs.execute("""
                INSERT INTO store (id, entry, updated)
                VALUES (?, ?, ?);
            """, (id_, dumps(entry), updated))
        except sqlite.IntegrityError:
            # Avoid database lockup.
            self.conn.rollback()
            raise

        # Index entry.
        entry['__updated__'] = updated.isoformat().split('.', 1)[0] + 'Z'
        indices = [(id_, k, v) for (k, v) in flatten(entry)]
        curs.executemany("""
            INSERT INTO flat (id, position, leaf)
            VALUES (?, ?, ?);
        """, indices)
        self.conn.commit()

        entry['__id__'] = id_
        entry['__updated__'] = updated
        return entry
        
    def delete(self, key):
        curs = self.conn.cursor()
        curs.execute("""
            DELETE FROM store
            WHERE id=?;
        """, (key,))

        curs.execute("""
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

        query = ["SELECT DISTINCT store.id, store.entry, store.updated FROM store LEFT JOIN flat ON store.id=flat.id"]
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
            query.append("store.id=?")
            params.insert(0, id_)
            if condition:
                query.append("AND")
        if condition:
            # Join all conditions with an OR.
            query.append("(%s)" % " OR ".join(condition))
        if leaves:
            query.append("GROUP BY store.id HAVING COUNT(*)=%d" % leaves)
        query.append("ORDER BY store.updated DESC")
        if size is not None:
            query.append("LIMIT %s" % size)
        if offset:
            query.append("OFFSET %s" % offset)
        query = ' '.join(query)

        curs = self.conn.cursor()
        if count:
            curs.execute("SELECT COUNT(*) FROM (%s)" % query, tuple(params))
            return curs.fetchone()[0]
        else:
            curs.execute(query, tuple(params))
            return format(curs.fetchall())

    def close(self):
        self.conn.close()
        del LOCAL.conns[self.location]


def format(results):
    entries = []
    for id_, entry, updated in results:
        entry = loads(entry)
        entry['__id__'] = id_
        entry['__updated__'] = updated
        entries.append(entry)

    return entries
