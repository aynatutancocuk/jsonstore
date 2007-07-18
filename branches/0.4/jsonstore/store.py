import re
from urllib import unquote
from urlparse import urljoin
import md5

from paste import httpexceptions
from paste.request import parse_dict_querystring, construct_url
from httpencode import parse_request, get_format
import cjson

from jsonstore.backends import EntryManager


DEFAULT_NUMBER_OF_ENTRIES = 10


def make_app(global_conf, dsn, **kwargs):
    """
    Create a JSON Atom store.

    Configuration should be like this::

        [app:jsonstore]
        use = egg:jsonstore
        dsn = driver://user:password@host:port/dbname

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
        func = getattr(self, '_%s' % environ['REQUEST_METHOD'])
        return func(environ, start_response)

    def _GET(self, environ, start_response):
        # Unserialize PATH_INFO to a JSON object.
        path_info = environ.get('PATH_INFO', '/')
        path_info = unquote(path_info)
        path_info = path_info.strip('/') or 'null'  # use null if path is /
        obj = cjson.decode(path_info)
        
        # Single entry.
        if isinstance(obj, (int, long, float, basestring)): 
            try:
                output = self.em.get_entry(obj)
            except KeyError:
                raise httpexceptions.HTTPNotFound()  # 404

        # Collection from listing or search.
        else:
            query = parse_dict_querystring(environ)
            size = int(query.get("size", DEFAULT_NUMBER_OF_ENTRIES))
            offset = int(query.get("offset", 0))

            # Return store listing.
            if obj is None:
                entries = self.em.get_entries(size+1, offset)
            # Return a JSON search.
            else:
                entries = self.em.search(obj, re.IGNORECASE, size+1, offset)

            # Check number of entries for a "next" entry.
            if len(entries) == size+1:
                entries.pop()  # remove "next" entry
                next = construct_url(environ,
                        querystring="size=%d&offset=%d" %
                        (size, offset+size))
            else:
                next = None
            
            output = {"collection": entries, "next": next}

        # Calculate etag.
        if '__etag__' in output: del output['__etag__'] 
        etag = md5.new(cjson.encode(output)).hexdigest()
        output['__etag__'] = etag

        app = self.format.responder(output,
                content_type='application/json',
                headers=[('Etag', etag)])
        return app(environ, start_response)

    def _POST(self, environ, start_response):
        entry = parse_request(environ, output_type='python')

        # Create the entry.
        output = self.em.create_entry(entry)

        # Generate new resource location.
        store = construct_url(environ, with_query_string=False, with_path_info=False)
        location = urljoin(store, str(output['__id__']))
        app = self.format.responder(output,
                content_type='application/json',
                headers=[('Location', location)])

        # Fake start response to return 201 status.
        def start(status, headers):
            return start_response("201 Created", headers)

        return app(environ, start)

    def _PUT(self, environ, start_response):
        entry = parse_request(environ, output_type='python')

        path_info = environ.get('PATH_INFO', '/')
        path_info = path_info.strip('/')
        id_ = unquote(path_info)
        if id_ is not None:
            entry.setdefault('__id__', id_)
            if id_ != entry['__id__']: raise httpexceptions.HTTPConflict()

        # Update entry.
        output = self.em.update_entry(entry)

        # Calculate etag.
        etag = md5.new(cjson.encode(output)).hexdigest()
        output['__etag__'] = etag

        app = self.format.responder(output,
                content_type='application/json',
                headers=[('Etag', etag)])
        return app(environ, start_response)

    def _DELETE(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '/')
        path_info = path_info.strip('/')
        id_ = unquote(path_info)

        self.em.delete_entry(id_)

        app = self.format.responder(None, content_type='application/json')
        return app(environ, start_response)

    def close(self):
        self.em.close()

