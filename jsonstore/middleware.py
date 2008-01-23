from paste.deploy.converters import aslist


def make_auth(app, global_conf, public_methods=None, attr='application'):
    public_methods = aslist(public_methods)
    return MethodAuth(app, public_methods, attr)


class MethodAuth(object):
    def __init__(self, app, public_methods=None, attr='application'):
        self.auth = app
        self.app = getattr(app, attr)
        self.public_methods = public_methods or []

    def __call__(self, environ, start_response):
        if environ['REQUEST_METHOD'] not in self.public_methods:
            return self.auth(environ, start_response)
        return self.app(environ, start_response)
