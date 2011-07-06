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

class PlaylistGenerator(object):
    def __init__(self):
        super(PlaylistGenerator, self).__init__()
        self.url_rlist = "http://www.e-radio.gr/cache/mediadata_1.js"
        self.file_rlist = 'radiolist.js'
        self.file_pls = 'playlist.pls'
        self.stations = []
        # Not required for now, radiolist.js is up-to-date.
        #self.get_radiolist()
        self.get_stations()

    def get_stations(self):
        # { mediatitle: "Άλφα Radio 96", city: "ΣΕΡΡΕΣ", mediaid: 1197, logo: "/logos/gr/mini/nologo.gif" }, 
        rxstr = r'mediatitle: "(?P<title>[^"]*)", city: "(?P<city>[^"]*)", mediaid: (?P<id>\d+), logo: "(?P<logo>[^"]*)"'
        rx = re.compile(rxstr)
        with codecs.open(self.file_rlist, 'r', 'utf-8') as f:
            text = f.readlines()
            for line in text:
                match = rx.search(line)
                if match:
                    self.stations.append(match.groupdict())
                    """ match.groupdict() example:
                    {
                        'logo': u'/logos/gr/mini/nologo.gif',
                        'title': u'\u0386\u03bb\u03c6\u03b1 Radio 96',
                        'id': u'1197',
                        'city': u'\u03a3\u0395\u03a1\u03a1\u0395\u03a3'
                    }
                    """

    def print_stations(self):
        for md in self.stations:
            print(u"Τίτλος : {0}\nΠόλη : {1}\nId : {2}\nLogo : {3}\n".format(
                md['title'], md['city'], md['id'], md['logo']))

    def get_radiolist(self):
        f = urllib.urlopen(self.url_rlist)
        text = f.read().replace("\r", "\n") # Strip \r characters
        utext = unicode(text, "iso-8859-7")
        with codecs.open(self.file_rlist, mode="w", encoding="utf-8") as f:
            f.write(utext)

    def make_pls(self):
        """
        Create a *.pls file.
        http://en.wikipedia.org/wiki/PLS_%28file_format%29
        """
        ns = len(self.stations)
        s = u""
        s += "[playlist]\n\n"
        for index, station in enumerate(self.stations):
            s += "File%d=%s\n" % (index, index)          # TODO put real url
            s += "Title%d=%s\n" % (index, station['title'])
            s += "Length=-1\n\n"
        s += "NumberofEntries=%d\n\n" % ns
        s += "Version=2\n"
        with codecs.open(self.file_pls, mode="w", encoding="utf-8") as f:
            f.write(s)
        print(s)

if __name__ == '__main__':
    playlist = PlaylistGenerator()
    playlist.print_stations()
    playlist.make_pls()
