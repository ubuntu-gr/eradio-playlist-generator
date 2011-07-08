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
import sys
from HTMLParser import HTMLParser
import shelve

# HTTP debug:
import httplib
httplib.HTTPConnection.debuglevel = 1

# Για τις δοκιμές κάνουμε λήψη 3 σελίδων μόνο. Στην πλήρη έκδοση το αφαιρούμε.
TESTCOUNT = 3

class radiodb():
    """ Used to store persistent data """
    def __init__(self):
        self.db_file = "cache.db"
        #flag="c" Open database for reading and writing, creating it if it doesn’t exist
        self.db = shelve.open(self.db_file, flag="c", writeback=True)

    def rebuild(self):
        """ Delete database and recreate it """
        # flag="n" = Always create a new, empty database, open for reading and writing
        self.db = shelve.open(self.db_file, flag="n", writeback=True)

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
        # self.src[0] => link, self.src[1] => type

class PlaylistGenerator(object):
    def __init__(self):
        super(PlaylistGenerator, self).__init__()
        self.url_rlist = "http://www.e-radio.gr/cache/mediadata_1.js"
        self.file_rlist = 'radiolist.js'
        self.file_pls = 'playlist.pls'
        self.file_xspf = 'playlist.xspf'
        self.stations = radiodb().db
        self.blacklist = ["1715", "1887", "307", "1803", "1758", "1805", "801"]
        self.get_stations()

    def get_stations(self):
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
        with codecs.open(self.file_rlist, 'r', 'utf-8') as f:
            text = f.readlines()
            for line in text:
                match = rx.search(line)
                if match:
                    d = match.groupdict()
                    did = d['id'].encode('utf-8')
                    if not self.stations.has_key(did):
                        # If not already in cache
                        self.stations[did] = d

    def get_radiolist(self):
        """ Reads radio list from self.url_rlist
        Writes to file self.file_rlist
        """
        f = urllib.urlopen(self.url_rlist)
        text = f.read().replace("\r", "\n") # Strip \r characters
        utext = unicode(text, "iso-8859-7")
        with codecs.open(self.file_rlist, mode="w", encoding="utf-8") as f:
            f.write(utext)

    def get_radiostation_files(self):
        """ Contacts e-radio.gr website, receives radio station link.
        match.groupdict() example:
        {
            'sid': u'1197',
            'cn': u'alfaserres',
            'weblink': u''
        }
        """
        url_main = "http://www.e-radio.gr/player/player.el.asp?sid="
        rxstr = r"playerX.asp\?sID=(?P<sid>\d+)&cn=(?P<cn>[^&]*)&weblink=(?P<weblink>[^&]*)"
        rx = re.compile(rxstr)
        for (index, sid) in enumerate(self.stations.keys()):
            print("Processing sid: {0}".format(sid))
            if self.stations[sid].has_key('url'):
                print("Skipping radio id {0} ({1}), already in cache".format(sid, self.stations[sid]["cn"]))
                continue #skip
            if sid in self.blacklist:
                print("Skipping radio id {0}, blacklisted".format(sid))
                continue #skip
            url_station = url_main + sid
            spider = Spider(url_station)
            src = spider.src
            print("src: {0}".format(src))
            if src:
                match = rx.search(src[0])
            else:
                print("Error! src is empty: {0} station dict: {1} link: {2}".format(src, self.stations[sid], url_station))
                #sys.exit(-1)
                self.blacklist.append(sid)
                print("Appended to blacklist and skipped: {0}".format(self.blacklist))
                continue
            if match:
                d = match.groupdict()
                self.stations[sid]['cn'] = d['cn']
                req = urllib.urlopen('http://www.e-radio.gr/asx/{0}.asx'.format(d['cn']))
                html = req.read()
                url = re.search(r'REF HREF = "(.*?)"', html)
                if url:
                    self.stations[sid]['url'] = url.group(1)
                else:
                    print("Couldn't find url for this station: {0} {1}".format(src, self.stations[sid]))
                    sys.exit(-1)
                print("station dict: {0} asx: http://www.e-radio.gr/asx/{1}.asx mms: {2} ".format(d, d["cn"], self.stations[sid]["url"]))
            elif src[1] == "asx":
                d = { 'sid': sid, 'cn': u'', 'weblink': u'' }
                self.stations[sid]['cn'] = d['cn']
                req = urllib.urlopen(src[0])
                html = req.read()
                url = re.search(r'REF HREF = "(.*?)"', html)
                if url:
                    self.stations[sid]['url'] = url.group(1)
                else:
                    print("Couldn't find url for this station: {0} {1}".format(src[0], self.stations[sid]))
                    sys.exit(-1)
                print("station dict (default): {0} asx: {1} mms: {2} ".format(d, src[0], self.stations[sid]["url"]))
            else:
                print("Error parsing radio station. src: {0} station dict: {1} link: {2}".format(src, self.stations[sid], url_station))
                sys.exit(-1)

            # Για 3 σταθμούς μόνο, για τη δοκιμή μας.
            #if index >= TESTCOUNT:
                #break

    def make_pls(self):
        """ Create a *.pls file.
        http://en.wikipedia.org/wiki/PLS_%28file_format%29
        """
        ns = len(self.stations.keys())
        s = u"[playlist]\n\n"
        for (index, sid) in enumerate(self.stations.keys()):
            if not self.stations[sid].has_key('url'):
                continue #skip
            s += "File%d=%s\n" % (index, self.stations[sid]['url'])
            s += "Title%d=%s\n" % (index, self.stations[sid]['title'])
            s += "Length=-1\n\n"
            #if index >= TESTCOUNT:
                #break
        s += "NumberofEntries=%d\n\n" % ns
        s += "Version=2\n"
        with codecs.open(self.file_pls, mode="w", encoding="utf-8") as f:
            f.write(s)

    def make_xspf(self):
        """ Create a *.xspf file.
        http://www.xspf.org
        """
        s = u'<?xml version="1.0" encoding="UTF-8"?>\n'
        s += '<playlist version="1" xmlns="http://xspf.org/ns/0/">\n'
        s += '    <trackList>\n'
        for (index, sid) in enumerate(self.stations.keys()):
            if not self.stations[sid].has_key('url'):
                continue #skip
            s += "        <track>\n"
            s += "            <location>%s</location>\n" % self.stations[sid]['url']
            s += "            <title>%s</title>\n" % self.stations[sid]['title']
            s += "            <annotation>%s</annotation>\n" % self.stations[sid]['city']
            s += "            <image>http://eradio.gr%s</image>\n" % self.stations[sid]['logo']
            s += "        </track>\n"
            #if index >= TESTCOUNT:
                #break
        s += "    </trackList>\n"
        s += "</playlist>\n"

        with codecs.open(self.file_xspf, mode="w", encoding="utf-8") as f:
            f.write(s)

if __name__ == '__main__':
    playlist = PlaylistGenerator()
    playlist.get_radiostation_files()
    playlist.stations.sync() # Write to cache
    playlist.make_pls()
    print(u'Created .PLS playlist file, playlist.pls')
    playlist.make_xspf()
    print(u'Created .XSPF playlist file, playlist.xspf')
