import urllib
import itertools
import operator
from datetime import datetime
import time
import threading
LOCAL = threading.local()

from uuid import uuid4
from simplejson import loads, dumps
from MySQLdb import connect

from jsonstore.operators import Operator, Equal, Exists
from jsonstore import flatten


class EntryManager(object):
    def __init__(self, location):
        self.location = location

        # Create table if it doesn't exist.
        self._create_table()

    @property
    def conn(self):
        if not hasattr(LOCAL, "conns"):
            LOCAL.conns = {}

        if self.location not in LOCAL.conns:
            params = split_location(self.location)
            LOCAL.conns[self.location] = connect(charset='utf8', **params)
        return LOCAL.conns[self.location]

    def _create_table(self):
        curs = self.conn.cursor()
        curs.execute("""
            CREATE TABLE IF NOT EXISTS store (
                id VARCHAR(255) PRIMARY KEY NOT NULL,
                entry TEXT,
                updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX (id));
        """)

        curs.execute("""
            CREATE TABLE IF NOT EXISTS flat (
                id VARCHAR(255),
                position CHAR(255),
                leaft TEXT,
                leafi INTEGER,
                leafr REAL,
                INDEX (position));
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
        curs.execute("""
            INSERT INTO store (id, entry, updated)
            VALUES (%s, %s, %s);
        """, (id_, dumps(entry), updated))

        # Index entry. We add some metadata (id, updated) and
        # put it on the flat table.
        entry['__updated__'] = updated.isoformat().split('.', 1)[0] + 'Z'
        curs.executemany("""
            INSERT INTO flat (id, position, leaft)
            VALUES (%s, %s, %s);
        """, [(id_, k, v) for (k, v) in flatten(entry)
                if isinstance(v, basestring)])
        curs.executemany("""
            INSERT INTO flat (id, position, leafi)
            VALUES (%s, %s, %s);
        """, [(id_, k, v) for (k, v) in flatten(entry)
                if isinstance(v, (int, long))])
        curs.executemany("""
            INSERT INTO flat (id, position, leafr)
            VALUES (%s, %s, %s);
        """, [(id_, k, v) for (k, v) in flatten(entry)
                if isinstance(v, float)])
        self.conn.commit()

        entry['__id__'] = id_
        entry['__updated__'] = updated
        return entry
        
    def delete(self, key):
        curs = self.conn.cursor()
        curs.execute("""
            DELETE FROM store
            WHERE id=%s;
        """, (key,))

        curs.execute("""
            DELETE FROM flat
            WHERE id=%s;
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

        query = ["SELECT DISTINCT store.id, store.entry, DATE_FORMAT(store.updated, '%%Y-%%m-%%dT%%TZ') FROM store LEFT JOIN flat ON store.id=flat.id"]
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

                if isinstance(leaf, Exists):
                    subquery.append("(position=%s AND (leaft NOTNULL OR leafi NOTNULL OR leafr NOTNULL))")
                elif isinstance(leaf.params[0], basestring):
                    subquery.append("(position=%%s AND leaft %s)" % str(leaf).replace('?', '%s'))
                elif isinstance(leaf.params[0], float):
                    subquery.append("(position=%%s AND leafr %s)" % str(leaf).replace('?', '%s'))
                elif isinstance(leaf.params[0], (int, long)):
                    subquery.append("(position=%%s AND leafi %s)" % str(leaf).replace('?', '%s'))
                params.extend(leaf.params)
                leaves += 1

            condition.append(' OR '.join(subquery))

        # Build query.
        if condition or id_ is not None:
            query.append("WHERE")
        if id_ is not None:
            query.append("store.id=%s")
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
        curs.execute("SET SESSION time_zone = 'SYSTEM';")
        if count:
            curs.execute("SELECT COUNT(*) FROM (%s) AS ITEMS" % query, tuple(params))
            return curs.fetchone()[0]
        else:
            curs.execute(query, tuple(params))
            return format(curs.fetchall())

    def close(self):
        self.conn.close()
        del LOCAL.conns[self.location]


def split_location(location):
    user, host = urllib.splituser(location)
    if user:
        user, passwd = urllib.splitpasswd(user)
    else:
        passwd = None

    host, db = urllib.splithost('//' + host)
    db = db.lstrip('/')
    host, port = urllib.splitport(host)

    kwargs = {}
    for name in ['user', 'passwd', 'host', 'port', 'db']:
        var = locals()[name]
        if var is not None: kwargs[name] = var
    return kwargs


def format(results):
    entries = []
    for id_, entry, updated in results:
        entry = loads(entry)
        entry['__id__'] = id_
        entry['__updated__'] = updated
        entries.append(entry)

    return entries
