=========
JSONstore
=========

Basic functionality
-------------------

JSONstore is a simple MicroApp_ that gives you a RESTful store for JSON objects. It uses the shove_ module for storage, supporting multiple storage backends, and is deployed as a WSGI_ application using `Python Paste`_.

Let's start with an example JSON store for Atom entries. We're going to deploy the store using Paste Deploy, so write the following configuration file::

    # jsonstore.ini
    [server:main]
    use = egg:Paste#http

    [app:main]
    use = egg:jsonstore
    dsn = memory://

We'll be using the memory storage, just for testing. Later this can be changed to a different, permanent, storage. We start the server by running the following command::

    $ paster serve jsonstore.ini

This will give us a store running at ``http://localhost:8080/``. We can check it to see that it's empty::

    $ curl http://localhost:8080/
    {"members": [], "next": null}

Not much exciting, huh? Let's add a JSON object representing an Atom entry. Here it is::

    {"title"   : "This is the first post",
     "author"  : {"name": "Rob de Almeida", "uri": "http://dealmeida.net/", "email": "roberto@dealmeida.net"},
     "content" : {"type": "text", "content": "This is my first post, testing the jsonstore WSGI microapp."},
     "summary" : "This is my first post here.",
     "category": [{"term": "weblog", "label": "Weblog stuff"},
                  {"term": "json", "label": "JSON"}]}

We will add this entry to the store by doing a POST request to the location ``http://localhost:8080``. Assuming you're reading this text in vim and you have ``curl`` installed, just type the following command::

    :28,33w ! curl -s -H "Content-Type: application/json" http://localhost:8080/ -d @-

When you type that command on your vim prompt, you'll see the body of the response from the server, showing the committed entry with a new id (should be the string "0") and an ``updated`` key/value pair. We can inspect the collection from the store again::

    $ curl http://localhost:8080/
    {"members": [{"href": "0", "entity": {"category": [{"term": "weblog", "label": "Weblog stuff"}, {"term": "json", "label": "JSON"}], "updated": "2007-05-02T23:15:58Z", "author": {"email": "roberto@dealmeida.net", "name": "Rob de Almeida", "uri": "http:\/\/dealmeida.net\/"}, "title": "This is the first post", "summary": "This is my first post here.", "content": {"content": "This is my first post, testing the jsonstore WSGI microapp.", "type": "text"}, "id": "0"}}], "next": null}

The protocol used by JSONstore is pretty much the one described by Joe Gregorio on his `RESTful JSON`_ article. The collection has a ``members`` object with a list of entries (or entities), and a ``next`` object pointing to the next "page" of entries -- this will be useful when the collection has a large number of entries, since usually only a few will be returned at each request.

Now that we have a JSON store, we can access individual entries::

    $ curl http://localhost:8080/0
    {"entity": {"category": [{"term": "weblog", "label": "Weblog stuff"}, {"term": "json", "label": "JSON"}], "updated": "2007-05-02T23:15:58Z", "title": "This is the first post", "author": {"uri": "http:\/\/dealmeida.net\/", "email": "roberto@dealmeida.net", "name": "Rob de Almeida"}, "summary": "This is my first post here.", "content": {"content": "This is my first post, testing the jsonstore WSGI microapp.", "type": "text"}, "id": "0"}}

To deleting a post is just a matter of doing a DELETE request to the proper resource. Since ``curl`` doesn't support DELETEs, we can emulate the request method using a query parameter::

    $ curl http://localhost:8080/0?REQUEST_METHOD=DELETE
    null

There we go, our store will again be empty. Let's recreate our initial entry::

    :28,33w ! curl -s -H "Content-Type: application/json" http://localhost:8080/ -d @-

To update the entry, we do a PUT request. First let's create our altered entry::

    {"title"   : "This is the second version of the first post",
     "author"  : {"name": "Rob de Almeida", "uri": "http://dealmeida.net/", "email": "roberto@dealmeida.net"},
     "content" : {"type": "text", "content": "This is my first post, testing the jsonstore WSGI microapp PUT."},
     "summary" : "This is my first post here, after some modifications",
     "category": [{"term": "weblog", "label": "Weblog stuff"},
                  {"term": "json", "label": "JSON"}]}

    :62,67w ! curl -s -H "Content-Type: application/json" http://localhost:8080/0?REQUEST_METHOD=PUT -d @-

And here's the modified version::

    $ curl http://localhost:8080/0
    {"entity": {"category": [{"term": "weblog", "label": "Weblog stuff"}, {"term": "json", "label": "JSON"}], "updated": "2007-05-02T23:25:59Z", "author": {"email": "roberto@dealmeida.net", "name": "Rob de Almeida", "uri": "http:\/\/dealmeida.net\/"}, "title": "This is the second version of the first post", "summary": "This is my first post here, after some modifications", "content": {"content": "This is my first post, testing the jsonstore WSGI microapp PUT.", "type": "text"}, "id": "0"}}

And that's more or less how it works. Now let's move to searching.


Searching
---------

Let's add a second entry to our store, to make searching more interesting::

    {"title"   : "This is the second post",
     "author"  : {"name": "Rob de Almeida", "uri": "http://dealmeida.net/", "email": "roberto@dealmeida.net"},
     "content" : {"type": "text", "content": "This is my second post, to test the search."},
     "summary" : "Testing search",
     "category": [{"term": "weblog", "label": "Weblog stuff"}]}

    :87,91w ! curl -s -H "Content-Type: application/json" http://localhost:8080/ -d @-

To search, we pass a JSON object that should match the stored entries. Here's an example to make it clear::

    $ curl -g 'http://localhost:8080/search/{"id":"0"}'
    {"members": [{"href": "0", "entity": {"category": [{"term": "weblog", "label": "Weblog stuff"}, {"term": "json", "label": "JSON"}], "updated": "2007-05-02T23:25:59Z", "title": "This is the second version of the first post", "author": {"uri": "http:\/\/dealmeida.net\/", "email": "roberto@dealmeida.net", "name": "Rob de Almeida"}, "summary": "This is my first post here, after some modifications", "content": {"content": "This is my first post, testing the jsonstore WSGI microapp PUT.", "type": "html"}, "id": "0"}}], "next": null}

Here we're searching for entries containing the object ``{"id":"0"}``, ie, entries that have the id equal to "0". Let's search by category now, looking for entries of the "json" category::

    $ curl -g 'http://localhost:8080/search/{"category":{"term":"json"}}'
    {"members": [{"href": "0", "entity": {"category": [{"term": "weblog", "label": "Weblog stuff"}, {"term": "json", "label": "JSON"}], "updated": "2007-05-02T23:25:59Z", "title": "This is the second version of the first post", "author": {"uri": "http:\/\/dealmeida.net\/", "email": "roberto@dealmeida.net", "name": "Rob de Almeida"}, "summary": "This is my first post here, after some modifications", "content": {"content": "This is my first post, testing the jsonstore WSGI microapp PUT.", "type": "html"}, "id": "0"}}], "next": null}

String in the search objects are actually regular expressions thar are matched (not searched) against the entries. If we want to search for all entries with the word "post" in its contents, here's how we would do that::

    $ curl -g 'http://localhost:8080/search/{"content":{"content":".*post"}}'
    {"members": [{"href": "1", "entity": {"category": [{"term": "weblog", "label": "Weblog stuff"}], "updated": "2007-05-02T23:32:03Z", "title": "This is the second post", "author": {"uri": "http:\/\/dealmeida.net\/", "email": "roberto@dealmeida.net", "name": "Rob de Almeida"}, "summary": "Testing search", "content": {"content": "This is my second post, to test the search.", "type": "text"}, "id": "1"}}, {"href": "0", "entity": {"category": [{"term": "weblog", "label": "Weblog stuff"}, {"term": "json", "label": "JSON"}], "updated": "2007-05-02T23:25:59Z", "title": "This is the second version of the first post", "author": {"uri": "http:\/\/dealmeida.net\/", "email": "roberto@dealmeida.net", "name": "Rob de Almeida"}, "summary": "This is my first post here, after some modifications", "content": {"content": "This is my first post, testing the jsonstore WSGI microapp PUT.", "type": "html"}, "id": "0"}}], "next": null}


Internal requests
-----------------

JSONstore uses HTTPencode_ for the conversion between JSON and other encodings. HTTPencode uses a lazy conversion mechanism, allowing you to do internal requests between WSGI apps that avoid the unnecessary serialization/deserialization when all you want are Python objects.

Here's an example to hopefully make things clearer. First, we'll create a composite WSGI application using Paste Deploy and wrapped in the ``recursive`` middleware::

    [server:main]
    use = egg:Paste#http

    [composite:main]
    use = egg:Paste#urlmap
    / = jsonstore
    /last = last
    filter-with = recursive

    [filter:recursive]
    use = egg:Paste#recursive

    [app:last]
    paste.app_factory = jsonstore.test:make_app

    [app:jsonstore]
    use = egg:jsonstore
    dsn = memory://

And here's the content of our other WSGI app that will do the internal requests::

    import httpencode

    def app(environ, start):
        headers = [("Content-type", "text/html")]
        start("200 OK", headers)

        h = httpencode.HTTP()
        data = h.request("http://localhost:8080/?size=1", output="python", wsgi_request=environ)
        return [str(data)]
                            
    def make_app(global_config, **local_conf):
        return app

This app simply grabs the last entry from the store by doing a request to ``http://localhost:8080/?size=1`` (this will return a single entry). Since the specified output is "python" and we're passing the WSGI environment, this request will be done internally avoiding the network and the serialization cycle.

Another advantage of HTTPencode is that is has a filter for converting between ``application/x-www-form-urlencoded`` or ``multipart/form-data`` and JSON (actually, Python objects). This means that you can add an entry by doing a POST from a typical HTML form -- the only downside is that it only supports "shallow" JSON objects without nested objects::

    $ curl -H "Content-type: application/x-www-form-urlencoded" http://localhost:8080/ -d 'title=One more title&magic number=42'
    {"entity": {"magic number": "42", "updated": "2007-05-03T00:12:11Z", "id": "3", "title": "One more title"}}


.. _MicroApp:       http://www.microapps.org/
.. _shove:          http://cheeseshop.python.org/pypi/shove
.. _WSGI:           http://wsgi.org/
.. _`Python Paste`: http://pythonpaste.org/
.. _`RESTful JSON`: http://bitworking.org/news/restful_json
.. _HTTPencode    : http://pythonpaste.org/httpencode/
