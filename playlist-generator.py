#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
from collections import namedtuple
import urllib

# Constants
URL_RADIOLIST = "http://www.e-radio.gr/cache/mediadata_1.js"
RADIOLIST = 'radiolist.js'
REGEX_PATTERN = r'(mediatitle): (".*?").*?(city): (".*?").*?(mediaid): (\d+).*?(logo): (".*?")'

MediaData = namedtuple('MediaData', ['title','city', 'id', 'logo'])

class PlaylistGenerator(object):
    def __init__(self):
        super(PlaylistGenerator, self).__init__()

        self.stations = []
        # Not required for now, radiolist.js is up-to-date.
        #self.get_radiolist()
        self.get_stations()

    def get_stations(self):
        with codecs.open(RADIOLIST, 'r', 'utf-8') as f:
            text = f.readlines()              # Create a list with the lines
            text = text[1:-1]                 # Remove first and last lines
            text[-1] += ","                   # Add a comma at the last entry

            for line in text:
                line = line[2:-4]             # clean-up each line
                fields = re.search(REGEX_PATTERN, line)
                self.stations.append(MediaData(fields.group(2), fields.group(4),
                                               fields.group(6), fields.group(8)))
    def print_stations(self):
        for md in self.stations:
            print(u"Τίτλος : {0}\nΠόλη : {1}\nId : {2}\nLogo : {3}\n".format(
                md.title, md.city, md.id, md.logo))
    
    def get_radiolist(self):
        f = urllib.urlopen(URL_RADIOLIST)
        result1 = f.read().replace("\r", "\n") # Strip \r characters
        result2 = unicode(result1, "iso-8859-7")
        #list = result2.split("\n")
        o = codecs.open(RADIOLIST, mode="w", encoding="utf-8")
        o.write(result2)
        o.close()

if __name__ == '__main__':
    playlist = PlaylistGenerator()
    playlist.print_stations()

