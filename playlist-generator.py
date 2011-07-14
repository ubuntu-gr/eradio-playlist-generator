#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2011 ubuntu-gr github team
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

# Authors : See https://github.com/organizations/ubuntu-gr/teams/69867 for the list of authors.
# Version : 0.1

# Imports
from __future__ import print_function
import codecs
import re
import urllib
from HTMLParser import HTMLParser
import multiprocessing
import sys

class Spider(HTMLParser):
    def __init__(self, url):
        HTMLParser.__init__(self)

        self.src = ""

        req = urllib.urlopen(url)
        self.feed(req.read())

    def handle_starttag(self, tag, attrs):
        if tag == "iframe":
            for attr in attrs:
                if attr[0] == "src" and attr[1].startswith("playerX"):
                    self.src = (attr[1], "playerx")
        elif tag == "embed":
            for attr in attrs:
                if attr[0] == "src" and attr[1].startswith("http://www.e-radio.gr/asx"):
                    self.src = (attr[1], "asx")

url_rlist = "http://www.e-radio.gr/cache/mediadata_1.js"
file_rlist = 'radiolist.js'
file_pls = 'playlist.pls'
file_xspf = 'playlist.xspf'
stations = {}
PROCESSES = 5

def get_stations():
    """ Creates a dictionary with station information.
    Appends the stations in self.stations list.
    match.groupdict() example:
    {
        'logo': u'/logos/gr/mini/nologo.gif',
        'title': u'\u0386\u03bb\u03c6\u03b1 Radio 96',
        'id': u'1197',
        'city': u'\u03a3\u0395\u03a1\u03a1\u0395\u03a3'
    }
    """
    # { mediatitle: "Άλφα Radio 96", city: "ΣΕΡΡΕΣ", mediaid: 1197, logo: "/logos/gr/mini/nologo.gif" }, 
    rxstr = r'mediatitle: "(?P<title>[^"]*)", city: "(?P<city>[^"]*)", mediaid: (?P<id>\d+), logo: "(?P<logo>[^"]*)"'
    rx = re.compile(rxstr)
    with codecs.open(file_rlist, 'r', 'utf-8') as f:
        text = f.readlines()
        for line in text:
            match = rx.search(line)
            if match:
                stations[match.groupdict()['id']] = match.groupdict()
    return len(stations)
    
def print_stations():
        for sid in stations.keys():
            print(u"Τίτλος : {0}\nΠόλη : {1}\nId : {2}\nLogo : {3}\n".format(
                stations[sid]['title'], stations[sid]['city'], sid, stations[sid]['logo']))

def get_radiolist():
    f = urllib.urlopen(url_rlist)
    text = f.read().replace("\r", "\n") # Strip \r characters
    utext = unicode(text, "iso-8859-7")
    with codecs.open(file_rlist, mode="w", encoding="utf-8") as f:
        f.write(utext)

def make_pls():
    """
    Create a *.pls file.
    http://en.wikipedia.org/wiki/PLS_%28file_format%29
    """
    ns = 0
    s = u""
    s += "[playlist]\n"
    for sid in stations.keys():
        try:
            url=stations[sid]['url']
            ns+=1
            s += "File%d=%s\n" % (ns, url)
            s += "Title%d=%s\n" % (ns, stations[sid]['title'])
            s += "Length%d=-1\n" % (ns)
        except:
            pass
    s += "NumberofEntries=%d\n" % ns
    s += "Version=2\n"
    with codecs.open(file_pls, mode="w", encoding="utf-8") as f:
        f.write(s)
    return ns

def make_xspf():
    """
    Create a *.xspf file.
    http://www.xspf.org
    """
    ns = 0
    s = u""
    s += '<?xml version="1.0" encoding="UTF-8"?>\n'
    s += '<playlist version="1" xmlns="http://xspf.org/ns/0/">\n'
    s += '    <trackList>\n'
    for sid in stations.keys():
        try:
            url = stations[sid]['url']
            ns += 1
            s += "        <track>\n"
            s += "            <location>%s</location>\n" % url.replace('&','&amp;')
            s += "            <title>%s</title>\n" % stations[sid]['title']
            s += "        </track>\n"
        except:
            pass
    s += "    </trackList>\n"
    s += "</playlist>\n"
    with codecs.open(file_xspf, mode="w", encoding="utf-8") as f:
        f.write(s)
    return ns

def get_urls(id):
    """ Contacts e-radio.gr website, receives radio station link.
    match.groupdict() example:
    {
    'sid': u'1197',
    'cn': u'alfaserres'
    'weblink': u''
    }
    """
    url_main = u"http://www.e-radio.gr/player/player.el.asp?sid="
    rxstr = r"playerX.asp\?sID=(?P<sid>\d+)&cn=(?P<cn>[^&]*)&weblink=(?P<weblink>[^&]*)"
    rx = re.compile(rxstr)
    url_station = url_main + id
    spider = Spider(url_station)
    src = spider.src
    if src:
        match = rx.search(src[0])
    else:
        return (id, None)
    if match:
        d = match.groupdict()
        req = urllib.urlopen('http://www.e-radio.gr/asx/' + d['cn'] + '.asx')
        html = req.read()
        url = re.search(r'REF HREF = "(.*?)"',html)
        if url:
            return (id, url.group(1))
    elif src[1] == "asx":
        req = urllib.urlopen(src[0])
        html = req.read()
        url = re.search(r'REF HREF = "(.*?)"', html)
        if url:
            return ( id, url.group(1))
    return (id, None)

def main():
    print("Getting list of stations")
    get_radiolist()
    print("Processing stations")
    print("{0:d} stations processed".format(get_stations()))
    print("Finding out stations' urls")
    pool = multiprocessing.Pool(processes=PROCESSES)
    lock = multiprocessing.Lock()
    sl = len(stations.keys())
    results = []
    for i in range(0,sl,PROCESSES):
        for j in range(PROCESSES):
            if i+j < sl:
                results.append(pool.apply_async(get_urls,(stations.keys()[i+j],)))
    for i in range(sl):
        (sid,url)=results[i].get()
        if url:
            stations[sid]['url']=url
        lock.acquire()
        print("Completed: {0:3d}%".format(((i+1)*100)/sl), end='\r')
        sys.stdout.flush()
        lock.release()
    print("")
    print("Saving pls file with {0:d} stations".format(make_pls()))
    print("Saving xspf file with {0:d} stations".format(make_xspf()))
    print("Done!")

if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()

   