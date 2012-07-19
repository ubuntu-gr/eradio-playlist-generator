#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2011-2012 ubuntu-gr github team
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
import urllib2
import sys
import os.path
import types
import httplib

from urlparse import urlparse
#from HTMLParser import HTMLParser
import socket
socket.setdefaulttimeout(10.0)


# cache.db
try:
    import cPickle as pickle
except ImportError:
    import pickle

class RadioDB():
    """ Used to store persistent data (self.db) """
    def __init__(self, service_template):
        self.db_file = service_template["db_file"]
        self.db = dict()
        self.load()

    def load(self):
        # Sets self.db
        if not os.path.isfile(self.db_file):
            self.dump()
        with open(self.db_file, "r") as f:
            self.db = pickle.load(f)

    def dump(self):
        # Writes self.db to self.db_file
        with open(self.db_file, "w") as f:
            pickle.dump(self.db, f)

#class Spider(HTMLParser):
    #def __init__(self, url):
        #HTMLParser.__init__(self)
        #self.src = ""
        #req = urllib.urlopen(url)
        #self.feed(req.read())

    #def handle_starttag(self, tag, attrs):
        #if tag == "iframe":
            #for attr in attrs:
                #if attr[0] == "src" and attr[1].startswith("playerX"):
                    #self.src = (attr[1], "playerx")
        #elif tag == "embed":
            #for attr in attrs:
                #if attr[0] == "src" and attr[1].startswith("http://www.e-radio.gr/asx"):
                    #self.src = (attr[1], "asx")
        ## self.src[0] => link, self.src[1] => type

class PlaylistGenerator(object):
    def __init__(self, service_template):
        super(PlaylistGenerator, self).__init__()
        # Init
        self.deftimeout = 10.0 # Default timeout
        self.service_template = service_template
        self.in_url = service_template["in_url"]
        self.in_file = service_template["in_file"]
        # Update local radio files (they contain raw unprocessed lists)
        #self.update_radio_list()
        # Initialize cache database
        self.radiodb = RadioDB(service_template)
        self.stations = self.radiodb.db
        self.blacklist = service_template["blacklist"]
        # Append stations from in_file to cache database
        self.get_stations()
        # Sync database
        self.radiodb.dump()

    def update_radio_list(self):
        """ Update local radio files (they contain raw unprocessed lists) """
        s = self.service_template["service"]
        print("Updating service: {0} - {1}".format(s, self.in_url))
        if s == "eradio":
            """ Updates radiolist.js from e-radio.gr """
            f = urllib.urlopen(self.in_url)
            text = f.read().replace("\r", "\n") # Strip \r characters
            utext = unicode(text, "iso-8859-7")
            with codecs.open(self.in_file, mode="w", encoding="utf-8") as f:
                f.write(utext)
        elif s == "24radio":
            """ Updates index.php from 24radio.gr """
            f = urllib.urlopen(self.in_url)
            text = f.read()
            utext = unicode(text, "utf-8")
            with codecs.open(self.in_file, mode="w", encoding="utf-8") as f:
                f.write(utext)

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
        s = self.service_template["service"]
        if s == "eradio":
            # { mediatitle: "Άλφα Radio 96", city: "ΣΕΡΡΕΣ", mediaid: 1197, logo: "/logos/gr/mini/nologo.gif" }, 
            rxstr = r'mediatitle: "(?P<title>[^"]*)", city: "(?P<city>[^"]*)", mediaid: (?P<id>\d+), logo: "(?P<logo>[^"]*)"'
            rx = re.compile(rxstr)
            with codecs.open(self.in_file, 'r', 'utf-8') as f:
                text = f.readlines()
                for line in text:
                    match = rx.search(line)
                    if match:
                        d = match.groupdict()
                        did = d['id'].encode('utf-8')
                        if not self.stations.has_key(did):
                            # If not already in cache
                            self.stations[did] = d
        elif s == "24radio":
            rxstr = r'<option value="code/station.php\?station_id=(\d+?)">(.+?)</option>'
            with codecs.open(self.in_file, 'r', 'utf-8') as f:
                text = f.read()
                match = re.findall(rxstr, text, re.S)
            if match:
                for each in match:
                    d = { "title": each[1], "id": each[0] }
                    did = d['id'].encode('utf-8')
                    if not self.stations.has_key(did):
                        # If not already in cache
                        self.stations[did] = d

    def parse_links(self):
        s = self.service_template["service"]
        if s == "eradio":
            self.parse_links_eradio()
        elif s == "24radio":
            self.parse_links_24radio()

    def get_urlobject(self, src, sid):
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "",
            "User-Agent": "NSPlayer/4.1.0.3856",
            "Pragma": "xClientGUID={c77e7400-738a-11d2-9add-0020af0a3278}",
            "Pragma": "xPlayStrm=1",
            "Icy-MetaData": "1",
        }
        request = urllib2.Request(src, data=None, headers=headers)
        opener = urllib2.build_opener(urllib2.HTTPHandler(debuglevel=1))    
        print("Getting url object of {0}".format(src))
        try:
            urlobject = opener.open(request, data=None, timeout=self.deftimeout)
        except urllib2.URLError, e:
            print("URL error: {0} {1}".format(src, e))
            self.add_to_blacklist(sid)
            return False #skip
        except socket.timeout:
            print("Error: Socket timeout: {0}".format(src))
            self.add_to_blacklist(sid)
            return False #skip
        except httplib.BadStatusLine:
            # TODO - Is there a way to ignore badstatusline?
            print("Error: Invalid url: {0} -- CHECK MANUALLY (probably rtmp or ICY protocol)".format(src))
            self.add_to_blacklist(sid)
            exit()
            #return False #skip
        except httplib.InvalidURL:
            print("Error: Invalid url: {0}".format(src))
            self.add_to_blacklist(sid)
            exit()
            return False #skip
        print("URL code: {0}".format(urlobject.getcode()))
        if not urlobject.getcode() == 200:
            print("ERROR: src http code not 200: {0} {1}".format(src, urlobject.getcode()))
            self.add_to_blacklist(sid)
            exit()
            return False #skip
        return urlobject

    def check_content_type(self, src, sid, mms=False):
        """ Check content type header and add or blacklist (or fail) """
        r = self.get_urlobject(src, sid)
        if type(r) == types.BooleanType:
            return False # error; skip
        if r.headers.has_key("Content-Type"):
            ctype = r.headers["Content-Type"]
            #print(h)
            if ctype == "video/x-ms-asf":
                # Possible recursion detected
                print("Content-type is: video/x-ms-asf - This should not happen (possible recursion detected).")
                self.parse_asx_playlist(src, sid, url_contents=r.read())
                return False
            elif ctype == "audio/x-mpegurl":
                print("Content-type audio/x-mpegurl - reparsing as m3u playlist")
                self.parse_m3u_playlist(src, sid, url_contents=r.read())
                return True
            elif "audio/" in ctype or ctype == "application/x-mms-framed":
                # DIRECT URL
                print("Received audio content-type: {0} - using as direct url".format(ctype))
                if mms:
                    # Use directly mmsh protocol
                    src = src.replace("http://", "mmsh://")
                self.add_to_radiodb(src, sid)
                return True
            elif ctype in ("text/html", "application/x-shockwave-flash"):
                # HTML OR FLASH - BLACKLIST
                print("Error: content-type: {0}".format(ctype))
                self.add_to_blacklist(sid)
                return False #skip
            else:
                # UNKNOWN/HTML? - FAIL
                print("Error: unknown content-type: {0} -- {1} -- CHECK MANUALLY".format(ctype, src))
                self.add_to_blacklist(sid)
                exit()
                return False #skip
        else:
            #Shoutcast / ICY Protocol - no http headers
            while True:
                line = r.readline().strip()
                if line:
                    if re.search("ICY 401 Service Unavailable", line):
                        print("Error: ICY 401 (Service Unavailable): {0}".format(src))
                        self.add_to_blacklist(sid)
                        return False #skip
                    ctype = re.search("content-type:\s?(.*)", line, re.I)
                    if ctype and "audio/" in ctype.group(1):
                        print("Matched content-type: {0} {1}".format(src, ctype.group(1)))
                        self.add_to_radiodb(src, sid)
                        return True
                else:
                    print("Error: Failed to find content-type: {0}".format(src))
                    self.add_to_blacklist(sid)
                    break
        print("No content-type detected? CHECK MANUALLY")
        exit()

    def parse_asx_playlist(self, src, sid, directurl=False, url_contents=''):
        """ Retrieve direct url from .asx playlist file. """
        if not url_contents:
            req = self.get_urlobject(src, sid)
            if type(req) == types.BooleanType:
                return False # error; skip
            html = req.read()
        else:
            html = url_contents
        rxurl = re.search(r'REF HREF\s?=\s?"(.*?)"', html, re.I+re.S)
        if not rxurl:
            if not directurl:
                # If it's not a direct url
                print("Error: Couldn't parse asx contents: {0}".format(src))
                self.add_to_blacklist(sid)
                return False #skip
            else:
                print("Error: Not .asx format, accepted as direct url: {0}".format(src))
                print("TODO")
                exit()
                ctype = self.check_content_type(src, sid)
                return True
        url = rxurl.group(1)
        # Strip whitespace
        url = url.rstrip()
        print("parse_asx_playlist: Found url: {0}".format(url))
        if url.startswith("mms://"):
            url = url.replace("mms://", "http://")
            self.check_content_type(url, sid, mms=True)
        else:
            self.check_content_type(url, sid)
        return True

    def parse_m3u_playlist(self, src, sid, url_contents=''):
        """ Retrieve direct url from .m3u playlist file. """
        if not url_contents:
            req = self.get_urlobject(src, sid)
            if type(req) == types.BooleanType:
                return False # error; skip
            text = req.read()
        else:
            text = url_contents
        match = re.search("(http://[^\s]*)", text, re.M)
        if match:
            url = match.group(1)
            print ("Discovered url {0}".format(url))
            ctype = self.check_content_type(url, sid)
        return True

    def add_to_blacklist(self, sid):
        self.blacklist.append(sid)
        print("Appended id {0} to blacklist {1}".format(sid, self.blacklist))

    def add_to_radiodb(self, src, sid):
        print("Using direct url {0} for radio id {1}".format(src, sid))
        self.stations[sid]['url'] = src
        self.radiodb.dump() # Sync database

    def parse_links_24radio(self):
        """ Contacts 24radio.gr website, tries to find radio's direct url and updates database. """
        url_main = "http://www.24radio.gr/code/station.php?station_id="
        for d in self.stations.itervalues():
            #print(i)
            t = d['title'].encode("utf-8")
            sid = d['id'].encode("utf-8")
            print("Title: {0} Link: {1}{2}".format(t, url_main, sid))
            if self.stations[sid].has_key('url'):
                print("Skipping radio id {0} ({1}), already in cache: {2}".format(sid, t, d['url']))
                continue #skip
            if sid in self.blacklist:
                print("Skipping radio id {0}, blacklisted".format(sid))
                continue #skip
            url_station = url_main + sid
            #Cannot use spider, not a clean html page
            print("Contacting {0}".format(url_station))
            urlo = self.get_urlobject(url_station, sid)
            text = urlo.read()
            m = re.search(r'<EMBED .*?src=["\']([^"\']*)["\']', text, re.S)
            if not m:
                print("ERROR: Could not match src, station dict: {0} link: {1}".format(self.stations[sid], url_station))
                self.add_to_blacklist(sid)
                continue
            src = m.group(1)
            if not "://" in src:
                src = "http://" + src #Assume http://
            print("src: {0}".format(src))
            urlp = urlparse(src)
            #strip whitespace characters
            src = src.rstrip()
            path = urlp.path.rstrip()
            #>>> urlparse.urlparse("http://www.example.com/test.asx?wow=1&boo=2")
            #>>> ParseResult(scheme='http', netloc='www.example.com', path='/test.asx', params='', query='wow=1&boo=2', fragment='')
            if urlp.scheme == "mms":
                print("Direct mms url detected.")
                src = src.replace("mms://", "http://")
                ctype = self.check_content_type(src, sid, mms=True)
                continue
            if path.endswith(".m3u"):
                print("src is m3u, looking for direct url")
                self.parse_m3u_playlist(src, sid)
                continue
            if path.endswith(".pls"):
                print("src is pls - TODO")
                exit()
            if path.endswith(".asx") or path.endswith(".wax"):
                # LINK IS .asx (playlist)
                print("src is asx, looking for direct url")
                self.parse_asx_playlist(src, sid)
                continue
            print("src not .asx, .pls, .m3u - checking content type")
            # Check content type and add or blacklist (or fail)
            ctype = self.check_content_type(src, sid)

    def parse_links_eradio(self):
        """ Contacts e-radio.gr website, receives radio station link and updates database.
            match.groupdict() example:
            {
                'sid': u'1197',
                'cn': u'alfaserres',
                'weblink': u''
            }
        """
        url_main = "http://www.e-radio.gr/player/mini.asp?c=000&pt=1&ppt=2&sid="

        for d in self.stations.itervalues():
            t = d['title'].encode("utf-8")
            sid = d['id'].encode("utf-8")
            print("\n\n=== Title: {0} Link: {1}{2}".format(t, url_main, sid))
            if self.stations[sid].has_key('url'):
                print("Skipping radio id {0} ({1}), already in cache: {2}".format(sid, t, d['url']))
                continue #skip
            if sid in self.blacklist:
                print("Skipping radio id {0}, blacklisted".format(sid))
                continue #skip
            
            url_station = url_main + sid
            print("Contacting {0}".format(url_station))
            urlo = self.get_urlobject(url_station, sid)
            text = urlo.read()
            m = re.search(r'<embed .*?src=["\']([^"\']*)["\']', text, re.S)
            if not m:
                print("ERROR: Could not match src, station dict: {0} link: {1}".format(self.stations[sid], url_station))
                self.add_to_blacklist(sid)
                continue
            src = m.group(1)
            if not "://" in src:
                src = "http://" + src #Assume http://
            print("src: {0}".format(src))
            urlp = urlparse(src)
            #strip whitespace characters
            src = src.rstrip()
            path = urlp.path.rstrip()
            #>>> urlparse.urlparse("http://www.example.com/test.asx?wow=1&boo=2")
            #>>> ParseResult(scheme='http', netloc='www.example.com', path='/test.asx', params='', query='wow=1&boo=2', fragment='')
            if urlp.scheme == "mms":
                print("Direct mms url detected.")
                src = src.replace("mms://", "http://")
                ctype = self.check_content_type(src, sid, mms=True)
                continue
            if path.endswith(".m3u"):
                print("src is m3u, looking for direct url")
                self.parse_m3u_playlist(src, sid)
                continue
            if path.endswith(".pls"):
                print("src is pls - TODO")
                exit()
            if path.endswith(".asx") or path.endswith(".wax"):
                # LINK IS .asx (playlist)
                print("src is asx, looking for direct url")
                self.parse_asx_playlist(src, sid)
                continue
            print("src not .asx, .pls, .m3u - checking content type")
            # Check content type and add or blacklist (or fail)
            ctype = self.check_content_type(src, sid)
        
        #rxstr = r"playerX.asp\?sID=(?P<sid>\d+)&cn=(?P<cn>[^&]*)&stitle=(?P<stitle>[^&]*)&pt=(?P<pt>[^&]*)&weblink=(?P<weblink>[^&]*)"
        #rx = re.compile(rxstr)
        #for (index, sid) in enumerate(self.stations.keys()):
            #print("Processing sid: {0}".format(sid))
            #if self.stations[sid].has_key('url'):
                #print("Skipping radio id {0} ({1}), already in cache".format(sid, self.stations[sid]["cn"]))
                #continue #skip
            #if sid in self.blacklist:
                #print("Skipping radio id {0}, blacklisted".format(sid))
                #continue #skip
                
            #url_station = url_main + sid
            #spider = Spider(url_station)
            #src = spider.src
            #print("src: {0}".format(src))
            #if src:
                #match = rx.search(src[0])
            #else:
                #print("Error! src is empty: {0} station dict: {1} link: {2}".format(src, self.stations[sid], url_station))
                ##sys.exit(-1)
                #self.blacklist.append(sid)
                #print("Appended to blacklist and skipped: {0}".format(self.blacklist))
                #continue
            #if match:
                #d = match.groupdict()
                #self.stations[sid]['cn'] = d['cn']
                #if d['weblink']: # If external weblink
                    #unquoted = urllib.unquote(d['weblink'])
                    #if (unquoted[0:3] != "http"):
                        #unquoted = "http://" + unquoted
                    #print("Found external weblink {0} - using as url".format(unquoted))
                    #self.stations[sid]['weblink'] = unquoted
                    #self.stations[sid]['url'] = unquoted
                #else:
                    #cnlink = 'http://www.e-radio.gr/asx/{0}.asx'.format(d['cn'])
                    #print("Did not find external weblink, trying {0}".format(cnlink))
                    #req = urllib.urlopen(cnlink)
                    #html = req.read()
                    #rxurl = re.search(r'REF HREF = "(.*?)"', html, re.I)
                    #if rxurl:
                        #self.stations[sid]['url'] = rxurl.group(1)
                #if not self.stations[sid].has_key('url') or not self.stations[sid]['url']:
                    #print("Couldn't find url for this station: {0} {1}".format(src, self.stations[sid]))
                    #sys.exit(-1)
                #print("station dict: {0} asx: http://www.e-radio.gr/asx/{1}.asx mms: {2} ".format(d, d["cn"], self.stations[sid]["url"]))
            #elif src[1] == "asx":
                #d = { 'sid': sid, 'cn': u'', 'weblink': u'' }
                #self.stations[sid]['cn'] = d['cn']
                #req = urllib.urlopen(src[0])
                #html = req.read()
                #url = re.search(r'REF HREF = "(.*?)"', html, re.I)
                #if url:
                    #self.stations[sid]['url'] = url.group(1)
                #else:
                    #print("Couldn't find url for this station: {0} {1}".format(src[0], self.stations[sid]))
                    #sys.exit(-1)
                #print("station dict (default): {0} asx: {1} mms: {2} ".format(d, src[0], self.stations[sid]["url"]))
            #else:
                #print("Error parsing radio station link (Could not match regex). src: {0} station dict: {1} link: {2}".format(src, self.stations[sid], url_station))
                #sys.exit(-1)

            #self.radiodb.dump() # Sync database

            ## Για 3 σταθμούς μόνο, για τη δοκιμή μας.
            ##if index >= TESTCOUNT:
                ##break

    def make_txt(self):
        """ Simple format, suitable for Greek Ubuntu ISO's radiostations.txt
        """
        s  = "# List of radio stations in Rhythmbox and Banshee\n"
        s += "#\n"
        s += "# Format: arbitrarily many lines with\n"
        s += "# URL; Genre; Name"
        for (index, sid) in enumerate(self.stations.keys()):
            if not self.stations[sid].has_key('url'):
                continue #skip
            s += self.stations[sid]['url']
            s += "; "
            s += "N/A; "
            s += self.stations[sid]['title']
            s += "\n"
        with codecs.open(self.service_template["out_file_txt"], mode="w", encoding="utf-8") as f:
            f.write(s)


    def make_pls(self):
        """ Create a *.pls file - http://en.wikipedia.org/wiki/PLS_%28file_format%29
        """
        ns = 0
        s = u'[playlist]\n'
        for (index, sid) in enumerate(self.stations.keys()):
            if not self.stations[sid].has_key('url'):
                continue #skip
            ns += 1
            s += u"File%d=%s\n" % (index, self.stations[sid]['url'])
            s += u"Title%d=%s\n" % (index, self.stations[sid]['title'])
            s += u"Length%d=-1\n" % (ns)
            #if index >= TESTCOUNT:
                #break
        s += u"NumberofEntries=%d\n" % ns
        s += u"Version=2\n"
        with codecs.open(self.service_template["out_file_pls"], mode="w", encoding="utf-8") as f:
            f.write(s)

    def make_xspf(self):
        """ Create a *.xspf file - http://www.xspf.org
        """
        s = u'<?xml version="1.0" encoding="UTF-8"?>\n'
        s += u'<playlist version="1" xmlns="http://xspf.org/ns/0/">\n'
        s += u'    <trackList>\n'
        for (index, sid) in enumerate(self.stations.keys()):
            if not self.stations[sid].has_key('url'):
                continue #skip
            s += u"        <track>\n"
            s += u"            <location>%s</location>\n" % self.stations[sid]['url'].replace("&", "&amp;")
            s += u"            <title>%s</title>\n" % self.stations[sid]['title']
            s += u"        </track>\n"
            #if index >= TESTCOUNT:
                #break
        s += u"    </trackList>\n"
        s += u"</playlist>\n"

        with codecs.open(self.service_template["out_file_xspf"], mode="w", encoding="utf-8") as f:
            f.write(s)

def go(service):
    if service == "eradio":
        service_template = {
            # e-radio.gr template
            "service"         : "eradio",
            "db_file"         : "eradio.cache.db",
            "in_url"          : "http://www.e-radio.gr/cache/mediadata_1.js",
            "in_file"         : 'eradio.radiolist.js',
            "out_file_pls"    : 'eradio.playlist.pls',
            "out_file_xspf"   : 'eradio.playlist.xspf',
            "out_file_txt"    : 'eradio.radiostations.txt',
            "blacklist"      : ['1702', '292', '270', '279', '521', '102', '528', '449', '1239', '103', '100', '107', '104', '902', '430', '1908', '1907', '1904', '1903', '1900', '850', '852', '819', '859', '6', '98', '1991', '1990', '1995', '1994', '743', '744', '745', '747', '232', '233', '1196', '1758', '1750', '140', '1889', '1884', '1882', '1881', '1880', '947', '689', '684', '683', '1818', '137', '490', '21', '2019', '401', '2014', '931', '2016', '1955', '1953', '1952', '1958', '829', '824', '827', '395', '83', '796', '792', '1879', '1136', '243', '249', '518', '170', '511', '514', '459', '451', '456', '1872', '178', '1878', '972', '180', '652', '1918', '1911', '1917', '1916', '861', '2023', '883', '929', '1966', '1962', '771', '207', '77', '73', '72', '1769', '1762', '1767', '1764', '1765', '216', '660', '769', '693', '694', '695', '1780', '1466', '124', '1829', '1828', '1824', '1821', '1820', '1822', '417', '498', '923', '316', '1922', '1923', '1926', '446', '1831', '781', '788', '62', '730', '733', '503', '465', '460', '1861', '2015', '1862', '961', '962', '408', '678', '1817', '876', '1893', '890', '1977', '1976', '1975', '1973', '1972', '951', '355', '808', '801', '953', '358', '210', '1783', '1777', '1776', '1771', '1075', '1779', '1778', '679', '677', '269', '55', '56', '538', '988', '981', '117', '111', '1859', '1850', '1853', '1854', '1856', '919', '1932', '1935', '1939', '138', '847', '843', '1987', '1981', '752', '224', '222', '950', '505', '725', '728', '1165', '1207', '1896', '1890', '473', '954', '1112', '2003', '1713', '488', '1807', '1801', '1860', '1808', '2006', '2007', '2004'],
        }
        #TODO: Exceptions (ICY without http headers): 222, 1112
    elif service == "24radio":
        service_template = {
            # 24radio.gr template
            "service"         : "24radio",
            "db_file"         : "24radio.cache.db",
            "in_url"          : "http://www.24radio.gr/",
            "in_file"         : '24radio.radiolist.html',
            "out_file_pls"    : '24radio.playlist.pls',
            "out_file_xspf"   : '24radio.playlist.xspf',
            "out_file_txt"    : '24radio.radiostations.txt',
            "blacklist"       : ['507', '818', '819', '347', '342', '343', '811', '815', '595', '718', '713', '710', '619', '427', '298', '296', '297', '295', '292', '293', '591', '592', '594', '596', '194', '606', '913', '196', '190', '271', '524', '525', '526', '527', '520', '528', '449', '442', '441', '440', '447', '445', '444', '108', '109', '102', '100', '101', '104', '907', '904', '36', '35', '641', '645', '88', '648', '435', '432', '433', '1002', '334', '337', '336', '332', '558', '98', '93', '92', '95', '94', '97', '153', '742', '745', '556', '550', '553', '234', '237', '230', '231', '232', '233', '144', '145', '143', '613', '611', '617', '946', '944', '945', '943', '940', '689', '684', '683', '682', '133', '131', '136', '135', '495', '490', '491', '492', '21', '407', '406', '404', '403', '400', '409', '934', '379', '378', '370', '376', '709', '705', '700', '701', '397', '395', '394', '83', '80', '398', '84', '85', '797', '794', '793', '798', '170', '585', '583', '581', '245', '246', '241', '148', '615', '248', '518', '511', '1006', '512', '517', '623', '620', '627', '624', '178', '176', '174', '198', '183', '654', '182', '180', '181', '653', '184', '652', '188', '187', '651', '947', '659', '568', '657', '326', '325', '328', '774', '204', '773', '206', '209', '208', '779', '76', '75', '74', '655', '358', '669', '667', '666', '662', '660', '215', '692', '693', '690', '697', '694', '699', '543', '540', '546', '548', '990', '120', '128', '214', '415', '416', '410', '413', '137', '319', '313', '310', '317', '316', '314', '496', '367', '952', '380', '381', '382', '383', '384', '385', '386', '387', '389', '785', '786', '781', '782', '789', '578', '572', '571', '577', '576', '575', '574', '258', '69', '255', '603', '730', '732', '735', '738', '502', '633', '635', '636', '637', '465', '461', '462', '164', '165', '167', '160', '963', '1103', '891', '896', '436', '356', '355', '802', '800', '804', '217', '768', '769', '762', '42', '760', '957', '321', '280', '282', '285', '677', '671', '672', '673', '261', '260', '264', '1031', '58', '55', '57', '56', '51', '52', '537', '536', '63', '533', '532', '539', '201', '988', '50', '115', '116', '112', '118', '207', '429', '428', '918', '916', '302', '303', '305', '306', '821', '954', '756', '758', '564', '567', '506', '229', '222', '220', '1026', '114', '1028', '720', '601', '602', '609', '469', '468', '959', '48', '49', '43', '464', '508', '488', '487', '485', '483', '482', '481', '480', '473', '477', '475', '810'],
        }
    playlist = PlaylistGenerator(service_template)
    playlist.parse_links()
    playlist.make_pls()
    print(u'Created .PLS playlist file, {0}'.format(service_template["out_file_pls"]))
    playlist.make_xspf()
    print(u'Created .XSPF playlist file, {0}'.format(service_template["out_file_xspf"]))
    playlist.make_txt()
    print(u'Created .txt playlist file, {0}'.format(service_template["out_file_txt"]))
    print("Blacklist: {0}".format(playlist.blacklist))

if __name__ == '__main__':
    go("eradio")
    #go("24radio")

