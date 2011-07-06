#!/usr/bin/python
# Get radio list, convert to utf-8 and write to file

import urllib
import codecs

f = urllib.urlopen("http://www.e-radio.gr/cache/mediadata_1.js")
result1 = f.read().replace("\r", "\n") # Strip \r characters
result2 = unicode(result1, "iso-8859-7")
#list = result2.split("\n")
o = codecs.open("radiolist.js", mode="w", encoding="utf-8")
o.write(result2)
o.close()
