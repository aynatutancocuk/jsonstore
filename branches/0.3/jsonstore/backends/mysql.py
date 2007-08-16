import urllib
import itertools
import operator
import datetime
import threading
LOCAL = threading.local()

from simplejson import loads, dumps
from MySQLdb import connect


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


def flatten(obj, keys=[]):
    key = '.'.join(keys)
    if isinstance(obj, (int, float, long, basestring)):
        yield key, obj
    else:
        if isinstance(obj, list):
            for item in obj:
                for pair in flatten(item, keys):
                    yield pair
        elif isinstance(obj, dict):
            for k, v in obj.items():
                for pair in flatten(v, keys + [k]):
                    yield pair


class EntryManager(object):
    def __init__(self, location):
        self.location = location

        # Create table if it doesn't exist.
        self._create_table()

    @property
    def conn(self):
        if not hasattr(LOCAL, "connections"):
            LOCAL.connections = {}

        if self.location not in LOCAL.connections:
            params = split_location(self.location)
            LOCAL.connections[self.location] = connect(**params)
        return LOCAL.connections[self.location]

    def _create_table(self):
        curs = self.conn.cursor()
        curs.execute("""
            CREATE TABLE IF NOT EXISTS store (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                entry TEXT,
                updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP);
        """)

        curs.execute("""
            CREATE TABLE IF NOT EXISTS flat (
                id INTEGER,
                position CHAR(255),
                leaf TEXT,
                INDEX (position));
        """)
        self.conn.commit()

    def create_entry(self, entry):
        assert isinstance(entry, dict), "Entry must be instance of ``dict``!"

        curs = self.conn.cursor()

        # __id__ and __updated__ can be overriden.
        if '__id__' in entry:
            # id must be an integer.
            id_ = int(entry.pop('__id__'))
        else:
            id_ = None
        if '__updated__' in entry:
            updated = entry.pop('__updated__')
            if not isinstance(updated, datetime.datetime):
                updated = datetime.datetime(
                    *(time.strptime(updated, '%Y-%m-%dT%H:%M:%SZ')[0:6]))
        else:
            updated = datetime.datetime.utcnow()

        # Store entry.
        curs.execute("""
            INSERT INTO store (id, entry, updated)
            VALUES (%s, %s, %s);
        """, (id_, dumps(entry), updated))
        id_ = curs.lastrowid

        # Index entry. We add some metadata (id, updated) and
        # put it on the flat table.
        entry['__id__'] = id_
        entry['__updated__'] = updated.isoformat().split('.', 1)[0] + 'Z'
        indices = [(id_, k, v) for (k, v) in flatten(entry)]
        curs.executemany("""
            INSERT INTO flat (id, position, leaf)
            VALUES (%s, %s, %s);
        """, indices)

        self.conn.commit()
        
        return self.get_entry(id_)
        
    def get_entry(self, key):
        curs = self.conn.cursor()
        curs.execute("SET SESSION time_zone = 'SYSTEM';")

        curs.execute("""
            SELECT id, entry, 
            DATE_FORMAT(updated, '%%Y-%%m-%%dT%%TZ')
            FROM store WHERE id=%s;
        """, (key,))
        id_, entry, updated = curs.fetchone()
        
        entry = loads(entry)
        entry['__id__'] = id_
        entry['__updated__'] = updated
        
        return entry

    def get_entries(self, size=None, offset=0): 
        curs = self.conn.cursor()
        curs.execute("SET SESSION time_zone = 'SYSTEM';")

        query = ["SELECT id, entry, DATE_FORMAT(updated, '%Y-%m-%dT%TZ') FROM store ORDER BY updated DESC"]
        if size is not None: query.append("LIMIT %s" % size)
        if offset: query.append("OFFSET %s" % offset)
        curs.execute(' '.join(query))

        entries = []
        for id_, entry, updated in curs.fetchall():
            entry = loads(entry)
            entry['__id__'] = id_
            entry['__updated__'] = updated
            entries.append(entry)

        return entries
        
    def delete_entry(self, key):
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

    def update_entry(self, new_entry): 
        assert isinstance(new_entry, dict), "Entry must be instance of ``dict``!"

        curs = self.conn.cursor()

        # __updated__ can be overriden.
        if '__updated__' in new_entry:
            updated = new_entry.pop('__updated__')
            if not isinstance(updated, datetime.datetime):
                updated = datetime.datetime(
                    *(time.strptime(updated, '%Y-%m-%dT%H:%M:%SZ')[0:6]))
        else:
            updated = datetime.datetime.utcnow()
        id_ = int(new_entry.pop('__id__'))

        curs.execute("""
            UPDATE store
            SET entry=%s, updated=%s
            WHERE id=%s;
        """, (dumps(new_entry), updated, id_))

        # Rebuild index.
        curs.execute("""
            DELETE FROM flat
            WHERE id=%s;
        """, (id_,))
        
        # Index entry.
        new_entry['__id__'] = id_
        new_entry['__updated__'] = updated.isoformat().split('.', 1)[0] + 'Z'
        indices = [(id_, k, v) for (k, v) in flatten(new_entry)]
        curs.executemany("""
            INSERT INTO flat (id, position, leaf)
            VALUES (%s, %s, %s);
        """, indices)

        self.conn.commit()
        
        return self.get_entry(id_)

    def search(self, obj, mode=0, size=None, offset=0):
        """
        Search database using a JSON object.
        
        The idea is here is to flatten the JSON object (the "key"), and search the index table for each leaf of the key using an OR. We then get those ids where the number of results is equal to the number of leaves in the key, since these objects match the whole key.
        
        """
        curs = self.conn.cursor()
        curs.execute("SET SESSION time_zone = 'SYSTEM';")

        # Flatten the JSON key object.
        pairs = list(flatten(obj))
        pairs.sort()
        groups = itertools.groupby(pairs, operator.itemgetter(0))

        query = ["SELECT store.id, store.entry, DATE_FORMAT(store.updated, '%%Y-%%m-%%dT%%TZ') FROM store LEFT JOIN flat ON store.id=flat.id"]
        condition = []
        params = []

        # Check groups from groupby, they should be joined within
        # using an OR.
        count = 0
        for (key, group) in groups:
            group = list(group)
            unused = [params.extend(t) for t in group]

            # Search mode.
            if mode == 0:
                # Plain match w/o regexp.
                subquery = ["(position=%s AND leaf=%s)" for t in group]
            elif mode == 1:
                # LIKE search.
                subquery = ["(position=%s AND leaf LIKE %s)" for t in group]
            elif mode == 2:
                # Regular expressions.
                subquery = ["(position=%s AND leaf REGEXP %s)" for t in group]

            condition.append(' OR '.join(subquery))
            count += len(unused)
        # Join all conditions with an OR.
        if condition:
            query.append("WHERE")
            query.append(' OR '.join(condition))
        if count: query.append('GROUP BY store.id HAVING count(*)=%d' % count)
        query.append("ORDER BY store.updated DESC")
        if size is not None: query.append("LIMIT %s" % size)
        if offset: query.append("OFFSET %s" % offset)

        curs.execute(' '.join(query), tuple(params))
        results = curs.fetchall()

        entries = []
        for id_, entry, updated in results:
            entry = loads(entry)
            entry['__id__'] = id_
            entry['__updated__'] = updated
            entries.append(entry)

        return entries

    def close(self):
        self.conn.close()
