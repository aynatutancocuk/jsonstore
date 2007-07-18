import os.path
import urllib
import itertools
import operator
import datetime
import threading
LOCAL = threading.local()

import cjson
from pysqlite2 import dbapi2 as sqlite


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
        self.location = location

        # Create table if it doesn't exist.
        if not os.path.exists(location): self._create_table()

    @property
    def conn(self):
        if not hasattr(LOCAL, "connection"):
            LOCAL.connection = sqlite.connect(self.location, 
                    detect_types=sqlite.PARSE_DECLTYPES|sqlite.PARSE_COLNAMES)
        return LOCAL.connection

    def _create_table(self):
        curs = self.conn.cursor()
        curs.execute("""
            CREATE TABLE store (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry TEXT,
                updated timestamp);
        """)

        curs.execute("""
            CREATE TABLE flat (
                id INTEGER,
                position CHAR(255),
                leaf TEXT);
        """)

        curs.execute("""
            CREATE INDEX position ON flat (position);
        """)

        self.conn.commit()

    def create_entry(self, entry):
        curs = self.conn.cursor()

        # Store entry.
        curs.execute("""
            INSERT INTO store (entry, updated)
            VALUES (?, ?);
        """, (cjson.encode(entry), datetime.datetime.now()))
        id_ = curs.lastrowid

        # Index entry.
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
        
        entry = cjson.decode(entry)
        entry['__id__'] = id_
        entry['__updated__'] = updated
        
        return entry

    def get_entries(self, size=None, offset=0): 
        curs = self.conn.cursor()

        query = ["SELECT id, entry, updated FROM store"]
        query.append("ORDER BY updated DESC")
        if size is not None: query.append("LIMIT %s" % size)
        if offset: query.append("OFFSET %s" % offset)
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
            WHERE id=?;
        """, (key,))

        curs.execute("""
            DELETE FROM flat
            WHERE id=?;
        """, (key,))

        self.conn.commit()

    def update_entry(self, new_entry): 
        curs = self.conn.cursor()

        curs.execute("""
            UPDATE store
            SET entry=?, updated=?
            WHERE id=?;
        """, (cjson.encode(new_entry), datetime.datetime.now(), new_entry['__id__']))

        # Rebuild index.
        curs.execute("""
            DELETE FROM flat
            WHERE id=?;
        """, new_entry['__id__'])
        
        # Index entry.
        indices = [(new_entry['__id__'], k, v) for (k, v) in flatten(new_entry)]
        curs.executemany("""
            INSERT INTO flat (id, position, leaf)
            VALUES (?, ?, ?);
        """, indices)

        self.conn.commit()
        
        return self.get_entry(id_)

    def search(self, obj, flags=0, size=None, offset=0):
        """
        Search database using a JSON object.
        
        The idea is here is to flatten the JSON object (the "key"), and search the index table for each leaf of the key using an OR. We then get those ids where the number of results is equal to the number of leaves in the key, since these objects match the whole key.
        
        """
        curs = self.conn.cursor()

        # Flatten the JSON key object.
        pairs = list(flatten(obj))
        pairs.sort()
        groups = itertools.groupby(pairs, operator.itemgetter(0))

        # Build search query. We use two separate queries, since MySQL has 
        # incredibly slow subqueries.
        # http://mysql2.mirrors-r-us.net/doc/refman/5.0/en/in-subquery-optimization.html
        # http://blog.ealden.net/article/mysql-50-and-in-subquery
        query = ["SELECT matches.id FROM (SELECT id, count(*) AS n FROM flat"]
        if groups: query.append("WHERE")
        condition = []
        params = []

        # Check groups from groupby, they should be joined within
        # using an OR.
        count = 0
        for (key, group) in groups:
            group = list(group)
            unused = [params.extend(t) for t in group]

            # Regular expressions are not supported.
            subquery = ["(position=? AND leaf=?)" for t in group]

            condition.append(' OR '.join(subquery))
            count += len(unused)
        # Join all conditions with an AND.
        query.append(' OR '.join(condition))
        query.append('GROUP BY id) AS matches WHERE matches.n=%d' % count)

        curs.execute(' '.join(query), tuple(params))
        ids = [str(row[0]) for row in curs.fetchall()]

        if ids:
            # Now we do a simple query to get the results.
            query = ["SELECT id, entry, updated FROM store WHERE id IN (%s)" % ', '.join(ids)]
            query.append("ORDER BY updated DESC")
            if size is not None: query.append("LIMIT %s" % size)
            if offset: query.append("OFFSET %s" % offset)
            curs.execute(' '.join(query))
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
