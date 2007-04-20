This is a RESTful store for JSON objects, that runs as a WSGI
application. Once you have it running at::

    http://localhost:8080

you can add entries in the following way::

    $ curl -H "Content-Type: application/json" http://localhost:8080/ --data-binary '{"title": "This is the title"}'
    {"updated": "2007-02-12T23:13:13Z", "id": "0", "title": "This is the title"}

Here it is, located at http://localhost:8080/0::

    $ curl -H "Content-Type: application/json" http://localhost:8080/0
    {"updated": "2007-02-12T23:13:13Z", "id": "0", "title": "This is the title"}

You can delete a resource by doing a DELETE request, or emulating
it with a GET/POST::

    $ curl -H "Content-Type: application/json" http://localhost:8080/0?REQUEST_METHOD=DELETE
    null

Or update it. First let's recreate it::
    
    $ curl -H "Content-Type: application/json" http://localhost:8080/ --data-binary '{"title": "This is the title"}'
    {"updated": "2007-02-12T23:24:33Z", "id": "0", "title": "This is the title"}

Now we update it, using a PUT::

    $ curl -H "Content-Type: application/json" http://localhost:8080/0?REQUEST_METHOD=PUT --data-binary '{"title": "No, *this* is the title"}'
    {"updated": "2007-02-12T23:24:54Z", "id": "0", "title": "No, *this* is the title"}

Data can also be inserted using a typical form POST, using the
``application/x-www-form-urlencoded`` or ``multipart/form-data``
content type)::

    $ curl -H "Content-type: application/x-www-form-urlencoded" http://localhost:8080/ --data 'title=One more title&magic number=42'
    {"magic number": "42", "updated": "2007-02-12T22:56:16Z", "id": "1", "title": "One more title"}

You can even use XML, that will be unserialized to a Python object
using a convention called "CarolFish" that I just invented::

    $ curl -H "Content-type: application/xml" http://localhost:8080/ --data-binary '<item><title>Title</title><author>John Doe</author><link>http://example.com</link><description>Excerpt</description></item>'
    {"item": [{"title": ["Title"]}, {"author": ["John Doe"]}, {"link": ["http://example.com"]}, {"description": ["Excerpt"]}], "updated": "2007-02-12T23:00:51Z", "id": "2"}

To list all entries just do a GET on the root::

    $ curl http://localhost:8080/
    [{"item": [{"title": ["Title"]}, {"author": ["John Doe"]}, {"link": ["http://example.com"]}, {"description": ["Excerpt"]}], "updated": "2007-02-12T23:25:18Z", "id": "2"}, {"magic number": "42", "updated": "2007-02-12T23:25:10Z", "id": "1", "title": "One more title"}, {"updated": "2007-02-12T23:24:54Z", "id": "0", "title": "No, *this* is the title"}]

You can search entries using a JSON encoded filter object. Let's search for entries with a title::

    $ curl -g 'http://localhost:8080/search/{"title":".+"}'
    [{"magic number": "42", "updated": "2007-02-12T23:25:10Z", "id": "1", "title": "One more title"}, {"updated": "2007-02-12T23:24:54Z", "id": "0", "title": "No, *this* is the title"}]
