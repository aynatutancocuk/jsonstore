This is a JSON-based Atom store, that runs as a WSGI application.
Once you have it running at::

    http://example.com

you can add Atom entries in the following way::

    $ curl -H "Content-Type: application/json" http://example.com/ --data-binary '{"title": "This is the title"}'
    {"updated": "2006-08-17T00:19:15Z", "id": "http://example.com/0", "title": "This is the title"}

Here it is, located at http://example.com/0::

    $ curl -H "Content-Type: application/json" http://example.com/0
    {"updated": "2006-08-17T00:19:15Z", "id": "http://example.com/0", "title": "This is the title"}

You can delete a resource by doing a DELETE request, or emulating
it with a GET/POST::

    $ curl -H "Content-Type: application/json" http://example.com/0?REQUEST_METHOD=DELETE
    {}

Or update it. First let's recreate it::
    
    $ curl -H "Content-Type: application/json" http://example.com/ --data-binary '{"title": "This is the title"}'
    {"updated": "2006-08-17T00:19:15Z", "id": "http://example.com/0", "title": "This is the title"}

Now we update it::

    $ curl -H "Content-Type: application/json" http://example.com/0?REQUEST_METHOD=PUT --data-binary '{"title": "No, *this* is the title"}'
    {"updated": "2006-08-17T00:25:14Z", "id": "http://example.com/0", "title": "No, *this* is the title"}

