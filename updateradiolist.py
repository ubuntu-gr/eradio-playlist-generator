#!/usr/bin/python
import urllib
import codecs

def main_eradio(inurl, outfile):
    """ Updates radiolist.js from e-radio.gr """
    f = urllib.urlopen(inurl)
    text = f.read().replace("\r", "\n") # Strip \r characters
    utext = unicode(text, "iso-8859-7")
    with codecs.open(outfile, mode="w", encoding="utf-8") as f:
        f.write(utext)

def main_24radio(inurl, outfile):
    """ Updates index.php from 24radio.gr """
    f = urllib.urlopen(inurl)
    text = f.read()
    utext = unicode(text, "utf-8")
    with codecs.open(outfile, mode="w", encoding="utf-8") as f:
        f.write(utext)

if __name__ == '__main__':
    a = "http://www.e-radio.gr/cache/mediadata_1.js"
    b = "eradio.radiolist.js"
    print("Contacting eradio")
    main_eradio(a, b)
    
    a2 = "http://www.24radio.gr"
    b2 = "24radio.radiolist.html"
    print("Contacting 24radio")
    main_24radio(a2, b2)
