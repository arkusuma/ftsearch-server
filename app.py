import bottle
from bottle import request, response

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
    try:
        response.content_type = 'application/json'
        resp = urllib2.urlopen(
                'http://www.filestube.com/search.html?%s' % 
                request.query_string)
        html = resp.read().decode('utf-8').replace('&nbsp;', ' ')

        parser = SearchParser()
        parser.feed(html)
        result = {'total': parser.total, 'index': parser.index, 'items': parser.items}
        return json.dumps(result)
    except:
        return json.dump({'total': 0})

@app.route('/api/link/<id:re:.*>')
def link(id):
    try:
        response.content_type = 'application/json'
        resp = urllib2.urlopen('http://www.filestube.com/%s' % id)
        html = resp.read().decode('utf-8')
        parser = LinkParser()
        parser.feed(html)
        result = [{'name': x[0], 'link': x[1]} for x in zip(parser.names, parser.links)]
        return json.dumps(result)
    except:
        return json.dumps([])

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
        if self._text != None:
            self._handle_text()
        if tag == 'div' and attrs.get('id') == 'newresult':
            self._item = {}
        elif self._item != None:
            self._tags.append({'tag': tag, 'attrs': attrs})
            if tag == 'a' and len(self._tags) == 1:
                href = attrs.get('href', '')
                self._item['id'] = href.replace('http://www.filestube.com/', '')
        elif tag == 'div' and attrs.get('class') == 'book3':
            self._in_book3 = True
        elif self._in_book3 and tag == 'span':
            self._in_span = True

    def handle_endtag(self, tag):
        if self._text != None:
            self._handle_text()
        if self._item != None:
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

class LinkParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.names = []
        self.links = []
        self._in_pre = False

    def handle_starttag(self, tag, attrs):
        if tag == 'a' and len(attrs) > 0 and attrs[0][0] == 'title':
            self.names.append(attrs[0][1])
        elif tag == 'pre':
            self._in_pre = True

    def handle_endtag(self, tag):
        if tag == 'pre':
            self._in_pre = False

    def handle_data(self, data):
        if self._in_pre:
            self.links = re.split('\s+', data.strip())

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
