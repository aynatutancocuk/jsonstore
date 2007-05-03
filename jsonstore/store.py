import re
import urllib
from urlparse import urljoin

from paste import httpexceptions
from paste.request import parse_dict_querystring, construct_url
from httpencode import parse_request, get_format
import simplejson

from jsonstore.entries import EntryManager


DEFAULT_NUMBER_OF_ENTRIES = 10


def make_app(global_conf, dsn='bsddb://posts.db', **kwargs):
    """
    Create a JSON Atom store.

    Configuration should be like this::

        [app:jsonstore]
        use = egg:jsonstore
        dsn = protocol://location

    """
    store = JSONStore(dsn)
    return store


class JSONStore(object):
    """
    A RESTful store based on JSON.

    """
    def __init__(self, dsn):
        self.em = EntryManager(dsn)
        self.format = get_format('json')

    def __call__(self, environ, start_response):
        self.environ = environ
        self.start = start_response

        path_info = environ.get('PATH_INFO', '/')
        dispatchers = [ ('/search/(?P<filters>.+)', self.search),
                        ('/(?P<id>.+)?', self.default), ]
        for regexp, func in dispatchers:
            p = re.compile(regexp)
            m = p.match(path_info)
            if m: return func(**m.groupdict())

        # 404.
        raise httpexceptions.HTTPNotFound()

    def default(self, id):
        """
        Dispatcher that uses the request method.

        """
        query = parse_dict_querystring(self.environ)
        method = query.get('REQUEST_METHOD') or self.environ['REQUEST_METHOD']
        func = getattr(self, '_%s' % method)
        return func(id)

    def _GET(self, id=None):
        """
        Return entry.

        """
        if id is None:
            query = parse_dict_querystring(self.environ)
            size = int(query.get("size", DEFAULT_NUMBER_OF_ENTRIES))
            offset = int(query.get("offset", 0))
            
            # Read members from the collection. We get the requested number of
            # entries plus the next one.
            entries = self.em.get_entries(size+1, offset)
            if len(entries) == size+1:
                entries.pop()  # remove "next" entry
                next = "size=%d&offset=%d" % (size, offset+size)
            else:
                next = None
            
            output = {"members": [{"href"  : entry["id"],
                                   "entity": entry,
                                  } for entry in entries],
                      "next": next}
        else: 
            try:
                output = {"entity": self.em.get_entry(id)}
            except KeyError:
                raise httpexceptions.HTTPNotFound()  # 404

        app = self.format.responder(output, content_type='application/json')
        return app(self.environ, self.start)

    def _POST(self, id):
        """
        Create a new entry.

        """
        entry = parse_request(self.environ, output_type='python')

        # Set id, if POSTed to specific resource.
        if id is not None:
            entry.setdefault('id', id)
            if not id == entry['id']: raise httpexceptions.HTTPConflict()
        
        # Create the entry.
        entry = self.em.create_entry(entry)

        # Generate new resource location.
        store = construct_url(self.environ, with_query_string=False, with_path_info=False)
        location = urljoin(store, entry['id'])
        app = self.format.responder({"entity": entry},
                                    content_type='application/json',
                                    headers=[('Location', location)])

        # Fake start response to return 201 status.
        def start(status, headers):
            return self.start("201 Created", headers)

        return app(self.environ, start)

    def _PUT(self, id):
        """
        Update an existing entry.

        """
        entry = parse_request(self.environ, output_type='python')

        if id is not None:
            entry.setdefault('id', id)
            if not id == entry['id']: raise httpexceptions.HTTPConflict()

        # Update entry.
        entry = self.em.update_entry(entry)

        app = self.format.responder({"entity": entry}, content_type='application/json')
        return app(self.environ, self.start)

    def _DELETE(self, id):
        """
        Delete an existing entry.

        """
        self.em.delete_entry(id)

        app = self.format.responder(None, content_type='application/json')
        return app(self.environ, self.start)

    def _HEAD(self, id):
        """
        Return headers only.

        """
        headers = [('Content-Encoding', 'utf-8'),
                   ('Content-Type', 'application/json')]
        self.start('200 OK', headers)
        return []

    def search(self, filters):
        query = parse_dict_querystring(self.environ)
        size = int(query.get("size", DEFAULT_NUMBER_OF_ENTRIES))
        offset = int(query.get("offset", 0))

        filters = urllib.unquote(filters)
        filters = simplejson.loads(filters)
        entries = self.em.search(filters, re.IGNORECASE, size, offset)

        if len(entries) == size+1:
            entries.pop()  # remove "next" entry
            next = "size=%d&offset=%d" % (size, offset+size)
        else:
            next = None
            
        output = {"members": [{"href"  : entry["id"],
                               "entity": entry,
                              } for entry in entries],
                  "next": next}

        app = self.format.responder(output, content_type='application/json')
        return app(self.environ, self.start)

    def close(self):
        self.em.close()

