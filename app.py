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

from urllib2 import urlopen
from bs4 import BeautifulSoup

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
        html = resp.read().decode('utf-8').replace('&nbsp;', ' ')

        # parse
        soup = BeautifulSoup(html)
        tags = soup.select('.book3 span')
        index = int(tags[0].string.split(' - ')[0])
        total = int(tags[1].string)
        items = []
        for tag in soup.select('.resultsLink'):
            text = tag.find_next_sibling('div').get_text().strip()
            m = re.match(r'(\S+)\s+ext:\s+\.(\S+)(\s+parts:\s+(\d+))?\s+(\d+ [KMG]B)\s+date:\s+(\S+)', text)
            if m:
                item = {}
                item['id'] = tag['href'].replace('http://www.filestube.com/', '')
                item['title'] = tag.get_text()
                item['site'] = m.group(1)
                item['ext'] = m.group(2)
                item['parts'] = int(m.group(4)) if m.group(4) else 1
                item['size'] = m.group(5)
                item['date'] = m.group(6)
                items.append(item)
        result = {'total': total, 'index': index, 'items': items}
    except:
        result = {'total': 0, 'index': 0, 'items': []}
    response.content_type = 'application/json'
    return json.dumps(result)

@app.route('/api/link/<id:path>')
def link(id):
    try:
        # load download link
        resp = urlopen('http://www.filestube.com/%s' % id)
        html = resp.read().decode('utf-8')

        # parse
        soup = BeautifulSoup(html)
        names = [tag['title'] for tag in soup.select('.mainltb2 a')]
        sizes = [tag.string for tag in soup.select('.tright')]
        links = re.split(r'\s+', soup.pre.string.strip())
        result = [{'name': name, 'size': size, 'link': link} \
                for name, size, link in zip(names, sizes, links)]
    except:
        result = []
    response.content_type = 'application/json'
    return json.dumps(result)

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
