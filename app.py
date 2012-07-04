import bottle
from bottle import request

import sys
import urllib2
import json
import re

from HTMLParser import HTMLParser
from htmlentitydefs import name2codepoint

app = bottle.Bottle()

@app.route('/')
def home():
    return '<h2>Hello World!</h2><p>Nothing to be viewed here.</p>'

@app.route('/api/search')
def search():
    resp = urllib2.urlopen(
            'http://www.filestube.com/search.html?%s' % 
            request.query_string)
    html = resp.read().decode('utf-8').replace('&nbsp;', ' ')

    parser = SearchParser()
    parser.feed(html)
    result = {'total': parser.total, 'index': parser.index, 'items': parser.items}
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
        if tag == 'div' and attrs.get('id') == 'newresult':
            self._item = {}
        elif self._item != None:
            if self._text != None:
                self._handle_text()
            self._tags.append({'tag': tag, 'attrs': attrs})
            if tag == 'a' and len(self._tags) == 1:
                href = attrs.get('href', '')
                self._item['id'] = href.replace('http://www.filestube.com/', '')
        elif tag == 'div' and attrs.get('class') == 'book3':
            self._in_book3 = True
        elif self._in_book3 and tag == 'span':
            self._in_span = True
        self._text = None

    def handle_endtag(self, tag):
        if self._item != None:
            if self._text != None:
                self._handle_text()
            if len(self._tags) == 0:
                self.items.append(self._item)
                self._item = None
            else:
                self._tags.pop()
        elif self._in_span:
            self._handle_text()
            self._in_span = False
        elif self._in_book3 and tag == 'div':
            self._in_book3 = False
        self._text = None

    def _handle_text(self):
        text = self._text
        if len(self._tags) == 1 and self._tags[-1]['tag'] == 'a':
            self._item['title'] = text
        elif len(self._tags) == 2 and self._tags[-1]['tag'] == 'span':
            m = re.search('(\d+ [KMG]B)\s+date:\s+(\d+-\d+-\d+)', text)
            if m != None:
                self._item['size'] = m.group(1)
                self._item['date'] = m.group(2)
        elif len(self._tags) == 3 and self._tags[-1]['tag'] == 'b':
            if 'style' in self._tags[-1]['attrs']:
                self._item['site'] = text
            elif text[:1] == '.':
                self._item['ext'] = text[1:]
        elif self._in_span:
            m = re.match('(\d+) - (\d+)', text)
            if m != None:
                self.index = int(m.group(1))
            elif re.match('\d+$', text) != None:
                self.total = int(text)

    def handle_data(self, data):
        if self._text == None:
            self._text = data
        else:
            self._text += data
        
    def handle_entityref(self, name):
        if name in name2codepoint:
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

if __name__ == '__main__':
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
    bottle.run(app, host=host, port=port, reloader=reload)
