import re
import datetime
import md5
from urlparse import urljoin

from paste import httpexceptions
from paste.request import construct_url, parse_dict_querystring
import simplejson

from atomstorage import EntryManager


class DateTimeAwareJSONEncoder(simplejson.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time types
    """
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%dT%H:%M:%SZ')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, datetime.time):
            return obj.strftime('%H:%M:%SZ')
        else:
            return super(self, DateTimeAwareJSONEncoder).default(obj)


def make_app(global_conf, dsn='shelve://posts.db', **kwargs):
    """
    Create a JSON Atom store.

    Configuration should be like this::

        [app:jsonstore]
        use = egg:jsonstore
        dsn = protocol://location
    """
    return JSONStore(dsn)


class JSONStore(object):
    """
    A RESTful Atom store based on JSON.
    """
    def __init__(self, dsn):
        self.em = EntryManager(dsn)

    def __call__(self, environ, start_response):
        self.environ = environ
        self.start = start_response

        # Allow overriding request method for clients that don't know PUT or DELETE.
        query = parse_dict_querystring(environ)
        req_method = query.get("REQUEST_METHOD") or environ['REQUEST_METHOD']
        method = getattr(self, '_%s' % req_method)

        path_info = environ.get('PATH_INFO', '/')
        m = re.match('/(?P<id>\d+)?', path_info)
        if m: return method(**m.groupdict())

        # Raise 404.
        raise httpexceptions.HTTPNotFound()
            
    def _GET(self, id):
        """
        Return entry.
        """
        if id is None:
            # Return an empty dict for clients introspecting the store.
            # Perhaps we should return a list of entries?
            headers = [('Content-Encoding', 'utf-8'),
                       ('Content-Type', 'application/json'), ]
            self.start("404 Not found", headers)
            return ['{}']
            
        try:
            entry = self.em.get_entry(id)
        except KeyError:
            raise httpexceptions.HTTPNotFound()

        # Update 'id' to point to location.
        location = construct_url(self.environ, with_query_string=False, with_path_info=False)
        entry['id'] = urljoin(location, entry['id'])

        # Convert to JSON.
        entry = simplejson.dumps(entry, cls=DateTimeAwareJSONEncoder)
        entry = entry.encode('utf-8')

        # Check etags.
        etag = md5.new(entry).hexdigest()
        incoming_etag = self.environ.get('HTTP_IF_NONE_MATCH', '')
        if etag == incoming_etag:
            self.start("304 Not Modified", [])
            return []

        headers = [('Content-Encoding', 'utf-8'),
                   ('Content-Type', 'application/json'),
                   ('ETag', etag), ]
        self.start('200 OK', headers)
        return [entry] 

    def _POST(self, id):
        """
        Create a new entry.
        """
        # Check for appropriate Content-Type
        content_type = self.environ.get('CONTENT_TYPE', '')
        content_type = content_type.split(';')[0]
        if content_type and content_type != 'application/json':
            self.start("400 Bad Request", [('Content-Type', 'text/plain')])
            return ["Wrong media type."] 
        
        content_length = self.environ.get("CONTENT_LENGTH", '')
        msg = self.environ['wsgi.input'].read(int(content_length))
        msg = simplejson.loads(msg)
        
        # Create the entry.
        entry = self.em.create_entry(msg)

        # Update 'id' to point to location.
        location = construct_url(self.environ, with_query_string=False, with_path_info=False)
        location = entry['id'] = urljoin(location, entry['id'])

        # Convert to JSON.
        entry = simplejson.dumps(entry, cls=DateTimeAwareJSONEncoder)
        entry = entry.encode('utf-8')

        headers = [('Content-Type', 'application/jsonrequest'),
                   ('Content-Encoding', 'utf-8'),
                   ('Location', location) ]
        self.start('201 Created', headers)
        return [entry]

    def _PUT(self, id):
        """
        Update an existing entry.
        """
        # Check for appropriate Content-Type
        content_type = self.environ.get('CONTENT_TYPE', '')
        content_type = content_type.split(';')[0]
        if content_type and content_type != 'application/json':
            self.start("400 Bad Request", [('Content-Type', 'text/plain')])
            return ["Wrong media type."]

        content_length = self.environ.get("CONTENT_LENGTH", '')
        msg = self.environ['wsgi.input'].read(int(content_length))
        entry = simplejson.loads(msg)

        # Fix message id from location to identifier.
        entry['id'] = id

        updated_entry = self.em.update_entry(entry)

        # Update 'id' to point to location.
        location = construct_url(self.environ, with_query_string=False, with_path_info=False)
        updated_entry['id'] = urljoin(location, entry['id'])

        # Convert to JSON.
        updated_entry = simplejson.dumps(updated_entry, cls=DateTimeAwareJSONEncoder)
        updated_entry = updated_entry.encode('utf-8')

        headers = [('Content-Encoding', 'utf-8'),
                   ('Content-Type', 'application/json') ]
        self.start('200 OK', headers)
        return [updated_entry] 

    def _DELETE(self, id):
        """
        Delete an existing entry.
        """
        self.em.delete_entry(id)

        self.start("200 OK", [('Content-Type', 'application/json')])
        return ['{}']

    def close(self):
        self.em.close()

