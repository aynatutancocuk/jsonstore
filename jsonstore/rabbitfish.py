"""
Format to convert between XML and Python using a JSON syntax.

Simple examples from `http://www.bramstein.nl/xlstjson`, using the
RabbitFish convention::

    >>> from StringIO import StringIO
    >>> print load_xml(StringIO("<alice>bob</alice>"), "")
    {'alice': 'bob'}
    >>> print load_xml(StringIO("<alice><bob>charlie</bob><david>edgar</david></alice>"), "")
    {'alice': {'bob': 'charlie', 'david': 'edgar'}}
    >>> print load_xml(StringIO("<alice><bob>charlie</bob><bob>david</bob></alice>"), "")
    {'alice': {'bob': ['charlie', 'david']}}
    >>> print load_xml(StringIO("<alice>bob<charlie>david</charlie>edgar</alice>"), "")
    {'alice': ['bob', {'charlie': 'david'}, 'edgar']}
    >>> print load_xml(StringIO('<alice charlie="david">bob</alice>'), "")
    {'alice': {'$': 'bob', '@charlie': 'david'}}

Converting back to XML::

    >>> print ''.join(dump_xml_iter({'alice': 'bob'}, ""))
    <alice>bob</alice>
    >>> print ''.join(dump_xml_iter({'alice': {'bob': 'charlie', 'david': 'edgar'}}, ''))
    <alice><bob>charlie</bob><david>edgar</david></alice>
    >>> print ''.join(dump_xml_iter({'alice': {'bob': ['charlie', 'david']}}, ''))
    <alice><bob>charlie</bob><bob>david</bob></alice>
    >>> print ''.join(dump_xml_iter({'alice': ['bob', {'charlie': 'david'}, 'edgar']}, ''))
    <alice>bob<charlie>david</charlie>edgar</alice>
    >>> print ''.join(dump_xml_iter({'alice': {'$': 'bob', '@charlie': 'david'}}, ''))
    <alice charlie="david">bob</alice>

Converting from Comment API to JSON::

    >>> print load_xml(StringIO("<item><title>Title</title><author>John Doe</author><link>http://example.com</link><description>Excerpt</description></item>"), "")
    {'item': {'author': 'John Doe', 'link': 'http://example.com', 'description': 'Excerpt', 'title': 'Title'}}

"""
try:
    import cElementTree as etree
except ImportError:
    import elementtree.ElementTree as etree

from httpencode.format import Format

def dump_xml_iter(data, content_type):
    # python -> xml
    root = build(data)[0]
    return [etree.tostring(root)]

def build(data):
    nodes = []
    for k, v in data.items():
        if isinstance(v, dict):
            node = etree.Element(k)
            for child in build(v):
                node.append(child)
            nodes.append(node)
        elif isinstance(v, list):
            for item in v:
                for child in build({k: item}):
                    nodes.append(child)
        else:
            node = etree.Element(k)
            node.text = v
            nodes.append(node)
    return nodes

def load_xml(fp, content_type):
    # xml -> python
    tree = etree.parse(fp)
    root = tree.getroot()
    out = {root.tag: parse(root)}
    return out

def parse(node):
    out = {}
    attrs = False
    for k, v in node.items():
        out["@%s" % k] = v
        attrs = True
    for child in node.getchildren():
        if child.tag in out:
            out[child.tag] = [out[child.tag]]
            out[child.tag].append(parse(child))
        else:
            print out
            out[child.tag] = parse(child)
        if child.tail:
            if not isinstance(out, list): out = [out]
            out.append(child.tail)
    if node.text:
        if attrs:
            out["$"] = node.text
        elif out:
            if not isinstance(out, list): out = [out]
            out.insert(0, node.text)
        else:
            out = node.text
    return out

rabbitfish = Format(
    'RabbitFish', ['text/xml', 'application/xml'],
    type='python',
    dump_iter=dump_xml_iter,
    load=load_xml,
    secure=True,
    )

def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    #_test()
    f = open('/Users/roberto/Projects/irate/irate.xml')
    print load_xml(f, '')

