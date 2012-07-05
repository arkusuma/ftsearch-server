# -*- coding: utf-8 -*-

"""
Copyright (c) 2012, Anugrah Redja Kusuma <anugrah.redja@gmail.com>

Utilization of the works is permitted provided that this
instrument is retained with the works, so that any entity
that utilizes the works is notified of this instrument.

DISCLAIMER: THE WORKS ARE WITHOUT WARRANTY.
"""

import bottle
from bottle import request, response

import sys
import json
import re

from urllib2 import urlopen, URLError, HTTPError
from HTMLParser import HTMLParser, HTMLParseError
from htmlentitydefs import name2codepoint

app = bottle.Bottle()

@app.route('/')
def home():
    return '<h2>Hello World!</h2><p>Nothing to be viewed here.</p>'

@app.route('/api/search')
def search():
    try:
        # load search result
        query = request.query_string
        resp = urlopen('http://www.filestube.com/search.html?%s' % query)
        html = resp.read().decode('utf-8')
        # parse
        parser = SearchParser()
        parser.feed(html)
        result = {'total': parser.total, 'index': parser.index, 'items': parser.items}
    except (URLError, HTTPError, HTMLParseError):
        result = {'total': 0}
    response.content_type = 'application/json'
    return json.dumps(result)

@app.route('/api/link/<id:path>')
def link(id):
    try:
        # load download link
        resp = urlopen('http://www.filestube.com/%s' % id)
        html = resp.read().decode('utf-8')
        # parse
        parser = LinkParser()
        parser.feed(html)
        result = [{'name': name, 'size': size, 'link': link} \
                for name, size, link in \
                zip(parser.names, parser.sizes, parser.links)]
    except (URLError, HTTPError, HTMLParseError):
        result = []
    response.content_type = 'application/json'
    return json.dumps(result)

class SearchParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.items = []
        self.index = 0
        self.total = 0
        self._tags = []
        self._item = None
        self._text = None
        self._in_book3 = False
        self._in_span = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self._text is not None:
            self._handle_text()
        if tag == 'div' and attrs.get('id') == 'newresult':
            self._item = {}
        elif self._item is not None:
            self._tags.append({'tag': tag, 'attrs': attrs})
            if tag == 'a' and len(self._tags) == 1:
                href = attrs.get('href', '')
                self._item['id'] = href.replace('http://www.filestube.com/', '')
        elif tag == 'div' and attrs.get('class') == 'book3':
            self._in_book3 = True
        elif self._in_book3 and tag == 'span':
            self._in_span = True

    def handle_endtag(self, tag):
        if self._text is not None:
            self._handle_text()
        if self._item is not None:
            if len(self._tags) == 0:
                self.items.append(self._item)
                self._item = None
            else:
                self._tags.pop()
        elif self._in_span:
            self._in_span = False
        elif self._in_book3 and tag == 'div':
            self._in_book3 = False

    def _handle_text(self):
        text = self._text
        self._text = None
        if len(self._tags) == 1 and self._tags[-1]['tag'] == 'a':
            self._item['title'] = text
        elif len(self._tags) == 2 and self._tags[-1]['tag'] == 'span':
            m = re.search(r'(\d+ [KMG]B)\s+date:\s+(\d+-\d+-\d+)', text)
            if m:
                self._item['size'] = m.group(1)
                self._item['date'] = m.group(2)
        elif len(self._tags) == 3 and self._tags[-1]['tag'] == 'b':
            if 'style' in self._tags[-1]['attrs']:
                self._item['site'] = text
            elif text[:1] == '.':
                self._item['ext'] = text[1:]
        elif self._in_span:
            m = re.match(r'(\d+) - (\d+)', text)
            if m:
                self.index = int(m.group(1))
            elif re.match(r'\d+$', text):
                self.total = int(text)

    def handle_data(self, data):
        if self._text is None:
            self._text = data
        else:
            self._text += data
        
    def handle_entityref(self, name):
        if name == 'nbsp':
            c = ' '
        elif name in name2codepoint:
            c = unichr(name2codepoint[name])
        else:
            c = '&' + name
        self.handle_data(c)
        
    def handle_charref(self, name):
        if name.startswith('x'):
            c = unichr(int(name[1:], 16))
        else:
            c = unichr(int(name))
        self.handle_data(c)

class LinkParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.names = []
        self.links = []
        self.sizes = []
        self._in_pre = False
        self._in_td = False

    def handle_starttag(self, tag, attrs):
        first_attr = attrs[0][0] if len(attrs) > 0 else ''
        attrs = dict(attrs)
        if tag == 'a' and first_attr == 'title':
            self.names.append(attrs['title'])
        elif tag == 'pre':
            self._in_pre = True
        elif tag == 'td' and attrs['class'] == "tright alt_width3":
            self._in_td = True

    def handle_endtag(self, tag):
        # our <pre> an <td> are innermost tag
        self._in_pre = False
        self._in_td = False

    def handle_data(self, data):
        if self._in_pre:
            self.links = re.split('\s+', data.strip())
        elif self._in_td:
            self.sizes.append(data)

if __name__ == '__main__':
    # Parse command line
    host = '0.0.0.0'
    port = 8080
    reload = False
    for arg in sys.argv[1:]:
        if arg == 'debug':
            bottle.debug(True)
        elif arg == 'reload':
            reload = True
        elif arg.isdigit():
            port = int(arg)
        else:
            host = arg

    # Run server
    bottle.run(app, host=host, port=port, reloader=reload)
