import os.path
import urllib
import itertools
import operator
from datetime import datetime
import time
import threading
import re

from uuid import uuid4
from simplejson import loads, dumps
from pysqlite2 import dbapi2 as sqlite

from jsonstore.operators import Operator, Equal


LOCAL = threading.local()
if not hasattr(LOCAL, 'conns'):
    LOCAL.conns = {}


# http://lists.initd.org/pipermail/pysqlite/2005-November/000253.html
def regexp(expr, item):
    p = re.compile(expr)
    return p.match(item) is not None


class EntryManager(object):
    def __init__(self, location):
        self.location = location
        if not os.path.exists(location):
            self._create_table()

    @property
    def conn(self):
        if self.location not in LOCAL.conns:
            LOCAL.conns[self.location] = sqlite.connect(self.location, 
                    detect_types=sqlite.PARSE_DECLTYPES|sqlite.PARSE_COLNAMES)
        LOCAL.conns[self.location].create_function("regexp", 2, regexp)
        return LOCAL.conns[self.location]

    def _create_table(self):
        curs = self.conn.cursor()
        curs.executescript("""
            CREATE TABLE store (
                id VARCHAR(255) NOT NULL,
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

    def create_entry(self, entry):
        assert isinstance(entry, dict), "Entry must be instance of ``dict``!"

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

        # Index entry. We add some metadata (id, updated) and
        # put it on the flat table.
        entry['__id__'] = id_
        entry['__updated__'] = updated.isoformat().split('.', 1)[0] + 'Z'
        indices = [(id_, k, v) for (k, v) in flatten(entry)]
        curs.executemany("""
            INSERT INTO flat (id, position, leaf)
            VALUES (?, ?, ?);
        """, indices)
        self.conn.commit()
        
        return self.get_entry(id_)
        
    def get_entry(self, key):
        curs = self.conn.cursor()
        curs.execute("""
            SELECT id, entry, updated FROM store
            WHERE id=?;
        """, (key,))
        id_, entry, updated = curs.fetchone()
        
        entry = loads(entry)
        entry['__id__'] = id_
        entry['__updated__'] = updated.isoformat().split('.', 1)[0] + 'Z'
        return entry

    def get_entries(self, size=None, offset=0): 
        query = ["SELECT id, entry, updated FROM store"]
        query.append("ORDER BY updated DESC")
        if size is not None:
            query.append("LIMIT %s" % size)
        if offset:
            query.append("OFFSET %s" % offset)
        curs = self.conn.cursor()
        curs.execute(' '.join(query))

        return format(curs.fetchall())

    def delete_entry(self, key):
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

    def update_entry(self, new_entry): 
        assert isinstance(new_entry, dict), "Entry must be instance of ``dict``!"

        id_ = new_entry['__id__']
        self.delete_entry(id_)
        return self.create_entry(new_entry)

    def search(self, obj, mode=0, size=None, offset=0):
        """
        Search database using a JSON object.
        
	The idea is here is to flatten the JSON object (the "key"),
	and search the index table for each leaf of the key using
	an OR. We then get those ids where the number of results
	is equal to the number of leaves in the key, since these
	objects match the whole key.
        
        """
        # Flatten the JSON key object.
        pairs = list(flatten(obj))
        pairs.sort()
        groups = itertools.groupby(pairs, operator.itemgetter(0))

        query = ["SELECT store.id, store.entry, store.updated FROM store LEFT JOIN flat ON store.id=flat.id"]
        condition = []
        params = []

        # Check groups from groupby, they should be joined within
        # using an OR.
        count = 0
        for (key, group) in groups:
            group = list(group)
            subquery = []
            for position, leaf in group:
                params.append(position)
                if not isinstance(leaf, Operator):
                    leaf = Equal(leaf)
                subquery.append("(position=? AND leaf %s)" % leaf)
                params.extend(leaf.params)
                count += 1

            condition.append(' OR '.join(subquery))
        # Join all conditions with an OR.
        if condition:
            query.append("WHERE")
            query.append(" OR ".join(condition))
        if count:
            query.append("GROUP BY store.id HAVING count(*)=%d" % count)
        query.append("ORDER BY store.updated DESC")
        if size is not None:
            query.append("LIMIT %s" % size)
        if offset:
            query.append("OFFSET %s" % offset)

        curs = self.conn.cursor()
        curs.execute(' '.join(query), tuple(params))
        results = curs.fetchall()

        return format(results)

    def close(self):
        self.conn.close()
        del LOCAL.conns[self.location]


def format(results):
    entries = []
    for id_, entry, updated in results:
        entry = loads(entry)
        entry['__id__'] = id_
        entry['__updated__'] = updated.isoformat().split('.', 1)[0] + 'Z'
        entries.append(entry)

    return entries


def quote_(name):
    return urllib.quote(name).replace('.', '%2E')


def flatten(obj, keys=[]):
    key = '.'.join(keys)
    if isinstance(obj, (int, float, long, basestring, Operator)):
        yield key, quote_(obj)
    else:
        if isinstance(obj, list):
            for item in obj:
                for pair in flatten(item, keys):
                    yield pair
        elif isinstance(obj, dict):
            for k, v in obj.items():
                for pair in flatten(v, keys + [quote_(k)]):
                    yield pair
