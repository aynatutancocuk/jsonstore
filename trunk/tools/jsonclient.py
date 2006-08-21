"""
Client for jsonstore.

Quick howto::

    $ jsonclient.py POST http://example.com/ entry.rfc822
    $ jsonclient GET http://example.com/0
    $ jsonclient DELETE http://example.com/0
    $ jsonclient PUT http://example.com/ entry.rfc822
"""
import sys
import email
import urlparse

import httplib2
import simplejson


def post(store, filename):
    inp = open(filename)
    msg = email.message_from_file(inp)
    inp.close()
    
    entry = {}
    entry['title'] = msg['subject']
    entry['content'] = {'content': msg.get_payload()}
    entry = simplejson.dumps(entry)

    # Post entry.
    h = httplib2.Http()
    resp, content = h.request(store, "POST", body=entry)

    entry = simplejson.loads(content)
    del msg['date']
    msg['date'] = entry['updated']
    del msg['id']
    msg['id'] = entry['id'][len(store):]

    outp = open(filename, 'w')
    outp.write(str(msg))
    outp.close()

    print resp['status']


def delete(id):
    h = httplib2.Http()
    resp, content = h.request('%s?REQUEST_METHOD=DELETE' % id, "POST")
    
    print resp['status']


def put(store, filename):
    inp = open(filename)
    msg = email.message_from_file(inp)
    inp.close()

    entry = {}
    entry['title'] = msg['subject']
    entry['content'] = {'content': msg.get_payload()}
    entry = simplejson.dumps(entry)

    # Post entry.
    h = httplib2.Http()
    location = urlparse.urljoin(store, msg['id'])
    resp, content = h.request('%s?REQUEST_METHOD=PUT' % location, "POST", body=entry)

    entry = simplejson.loads(content)
    del msg['date']
    msg['date'] = entry['updated']

    outp = open(filename, 'w')
    outp.write(str(msg))
    outp.close()

    print resp['status']


def get(id):
    h = httplib2.Http()
    resp, content = h.request(id, "GET")

    entry = simplejson.loads(content)
    msg = email.message_from_string('')
    msg['date'] = entry['updated']
    msg['subject'] = entry['title']
    msg.set_payload(entry['content']['content'])
    
    print msg
    

if __name__ == '__main__':
    method = sys.argv[1].lower()

    {'post'  : post,
     'delete': delete,
     'put'   : put,
     'get'   : get,
    }[method](*sys.argv[2:])
