import urllib
import itertools
import operator
import threading
LOCAL = threading.local()

import cjson
from MySQLdb import connect


# TODO: regular expression


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
        # Create connection.
        self.params = split_location(location)

        # Create table if it doesn't exist.
        self._create_table()

    @property
    def conn(self):
        if not hasattr(LOCAL, "connection"):
            LOCAL.connection = connect(**self.params)
        return LOCAL.connection

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
        curs = self.conn.cursor()

        # Store entry.
        curs.execute("""
            INSERT INTO store (entry)
            VALUES (%s);
        """, (cjson.encode(entry),))
        id_ = curs.lastrowid

        # Index entry.
        indices = [(id_, k, v) for (k, v) in flatten(entry)]
        curs.executemany("""
            INSERT INTO flat (id, position, leaf)
            VALUES (%s, %s, %s);
        """, indices)

        self.conn.commit()
        
        return self.get_entry(id_)
        
    def get_entry(self, key):
        curs = self.conn.cursor()

        curs.execute("""
            SELECT id, entry, updated FROM store
            WHERE id=%s;
        """, (key,))
        id_, entry, updated = curs.fetchone()
        
        entry = cjson.decode(entry)
        entry['__id__'] = id_
        entry['__updated__'] = updated
        
        return entry

    def get_entries(self, size=None, offset=0): 
        curs = self.conn.cursor()

        query = ["SELECT id, entry, updated FROM store"]
        if size is not None: query.append("LIMIT %s" % size)
        if offset: query.append("OFFSET %s" % offset)
        query.append("ORDER BY updated DESC")
        curs.execute(' '.join(query))

        entries = []
        for id_, entry, updated in curs.fetchall():
            entry = cjson.decode(entry)
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
        curs = self.conn.cursor()

        curs.execute("""
            UPDATE store
            SET entry=%s
            WHERE id=%s;
        """, (cjson.encode(new_entry), new_entry['__id__']))

        # Rebuild index.
        curs.execute("""
            DELETE FROM flat
            WHERE id=%s;
        """, new_entry['__id__'])
        
        # Index entry.
        indices = [(new_entry['__id__'], k, v) for (k, v) in flatten(new_entry)]
        curs.executemany("""
            INSERT INTO flat (id, position, leaf)
            VALUES (%s, %s, %s);
        """, indices)

        self.conn.commit()
        
        return self.get_entry(id_)

    def search(self, obj, flags=0, size=None, offset=0):
        pairs = list(flatten(obj))
        pairs.sort()
        groups = itertools.groupby(pairs, operator.itemgetter(0))

        curs = self.conn.cursor()

        # Build search query. We use two separate queries, since MySQL has 
        # incredibly slow subqueries.
        # http://mysql2.mirrors-r-us.net/doc/refman/5.0/en/in-subquery-optimization.html
        # http://blog.ealden.net/article/mysql-50-and-in-subquery
        query = ["SELECT matches.id id FROM (SELECT id, count(*) AS n FROM flat"]
        if groups: query.append("WHERE")
        condition = []
        params = []

        # Check groups from groupby, they should be joined within
        # using an OR.
        count = 0
        for (key, group) in groups:
            group = list(group)
            unused = [params.extend(t) for t in group]
            subquery = ["(position=%s AND leaf=%s)" for t in group]
            condition.append(' OR '.join(subquery))
            count += len(unused)
        # Join all conditions with an AND.
        condition = ' OR '.join(condition)
        query.append(condition)
        query.append('GROUP BY id) AS matches WHERE matches.n=%d' % count)  # close subselect
        query = ' '.join(query)
        print query.replace("%s", "'%s'") % tuple(params)
        curs.execute(query, tuple(params))
        ids = [str(row[0]) for row in curs.fetchall()]

        if ids:
            query = ["SELECT id, entry, updated FROM store WHERE id IN (%s)" % ', '.join(ids)]
            if size is not None: query.append("LIMIT %s" % size)
            if offset: query.append("OFFSET %s" % offset)
            query.append("ORDER BY updated DESC")
            query = ' '.join(query)
            curs.execute(query)
            results = curs.fetchall()
        else:
            results = []

        entries = []
        for id_, entry, updated in results:
            entry = cjson.decode(entry)
            entry['__id__'] = id_
            entry['__updated__'] = updated
            entries.append(entry)

        return entries

    def close(self):
        self.conn.close()
