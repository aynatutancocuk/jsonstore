import re
from urllib import unquote
from urlparse import urljoin
from datetime import datetime
from sha import sha

from webob import Request, Response
from simplejson import loads, dumps, JSONEncoder

from jsonstore.store import EntryManager
from jsonstore import rison
from jsonstore import operators


def make_app(global_conf, **kwargs):
    return JSONStore(**kwargs)


class DatetimeEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat().split('.', 1)[0] + 'Z'


class JSONStore(object):
    def __init__(self, **kwargs):
        self.em = EntryManager(**kwargs)

    def __call__(self, environ, start_response):
        req = Request(environ)
        func = getattr(self, req.method)
        res = func(req)
        return res(environ, start_response)

    def GET(self, req):
        path_info = req.path_info.lstrip('/') or '{}'  # empty search
        path_info = unquote(path_info)
        obj = load_entry(path_info)

        jsonp = req.GET.get('jsonp') or req.GET.get('callback')
        size = req.GET.get('size')
        offset = req.GET.get('offset')

        if isinstance(obj, (int, long, float, basestring)):
            try:
                result = self.em.search(__id__=obj)[0]
                items = 1
            except IndexError:
                return Response(status='404 Not Found')
        else:
            obj = replace_operators(obj)
            items = self.em.search(obj, count=True)
            result = self.em.search(obj, size, offset)
        
        body = dumps(result, cls=DatetimeEncoder)
        etag = '"%s"' % sha(body).hexdigest()
        if etag in req.if_none_match:
            return Response(status='304 Not Modified')

        if jsonp:
            body = jsonp + '(' + body + ')'
            content_type = 'text/javascript'
        else:
            content_type = 'application/json'

        return Response(
                body=body,
                content_type=content_type,
                charset='utf8',
                headerlist=[('X-ITEMS', str(items)), ('etag', etag)])

    def HEAD(self, req):
        response = self.GET(req)
        response.body = ''
        return response

    def POST(self, req):
        entry = load_entry(req.body)
        result = self.em.create(entry)
        body = dumps(result, cls=DatetimeEncoder)
        etag = '"%s"' % sha(body).hexdigest()
        location = urljoin(req.application_url, result['__id__'])

        return Response(
                status='201 Created',
                body=body,
                content_type='application/json',
                charset='utf8',
                headerlist=[('Location', location), ('etag', etag)])

    def PUT(self, req):
        entry = load_entry(req.body)
        url_id = req.path_info.lstrip('/')
        if '__id__' not in entry:
            entry['__id__'] = url_id
        elif url_id != entry['__id__']:
            return Response(status='409 Conflict')

        # Conditional PUT.
        old = self.em.search(__id__=url_id)
        if old:
            etag = '"%s"' % sha(dumps(old[0], cls=DatetimeEncoder)).hexdigest()
            if etag not in req.if_match or (
                    req.if_unmodified_since and 
                    req.if_unmodified_since < old[0]['updated']):
                return Response(status='412 Precondition Failed')

        result = self.em.update(entry)
        body = dumps(result, cls=DatetimeEncoder)
        etag = '"%s"' % sha(body).hexdigest()

        return Response(
                body=body,
                content_type='application/json',
                charset='utf8',
                headerlist=[('etag', etag)])
        
    def DELETE(self, req):
        id_ = req.path_info.lstrip('/')
        self.em.delete(id_)

        return Response(
                status='204 No Content',
                body='',
                content_type='application/json',
                charset='utf8')


def load_entry(s):
    try:
        entry = loads(s)
    except ValueError:
        try:
            entry = rison.loads(s)
        except rison.ParserException:
            entry = s
    return entry


def replace_operators(obj):
    for k, v in obj.items():
        if isinstance(v, dict):
            obj[k] = replace_operators(v)
        elif isinstance(v, list):
            for i, item in enumerate(v):
                obj[k][i] = parse_op(item)
        else:
            obj[k] = parse_op(v)
    return obj


def parse_op(obj):
    if not isinstance(obj, basestring):
        return obj

    for op in operators.__all__:
        m = re.match(op + r'\((.*?)\)', obj)
        if m:
            operator = getattr(operators, op)
            args = m.group(1)
            args = loads('[' + args + ']')
            return operator(*args)
    return obj


if __name__ == '__main__':
    from paste.httpserver import serve
    app = JSONStore('sqlite://test.db')
    serve(app, port=8081)
