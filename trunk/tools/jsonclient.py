"""
Client for jsonstore.

Quick howto::

    $ jsonclient.py --view http://example.com/0
    $ jsonclient.py --edit http://example.com/ [entry.rfc822]
    $ jsonclient.py --delete http://example.com/0
"""
import sys
import email
import urlparse

import httplib2
import simplejson


def edit(store, filename=None):
    if filename is None:
        inp = sys.stdin
    else:
        inp = open(filename)
    msg = email.message_from_file(inp)
    
    entry = {}
    entry['title'] = msg['subject']
    entry['content'] = {'content': msg.get_payload()}
    entry = simplejson.dumps(entry)

    # Post entry.
    h = httplib2.Http()
    if msg['id']:
        location = urlparse.urljoin(store, msg['id'])
        resp, content = h.request('%s?REQUEST_METHOD=PUT' % location, "POST", body=entry)
    else:
        resp, content = h.request(store, "POST", body=entry)

    entry = simplejson.loads(content)
    del msg['date']
    msg['date'] = entry['updated']
    del msg['id']
    msg['id'] = entry['id'][len(store):]

    if filename is None:
        outp = sys.stdout
    else:
        outp = open(filename, 'w')
    outp.write(str(msg))

    print resp['status']


def delete(id):
    h = httplib2.Http()
    resp, content = h.request('%s?REQUEST_METHOD=DELETE' % id, "POST")
    
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
