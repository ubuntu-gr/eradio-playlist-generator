#!/usr/bin/python
# Example: ./getradioinfo.py 24radio.cache.db -showall

import sys
try:
    import cPickle as pickle
except ImportError:
    import pickle
import pprint

try:
    rfile = sys.argv[1]
    rcomm = sys.argv[2]
except IndexError:
    exit("Try:\n ./getradioinfo.py <cache_file> -show <id>\n\
 ./getradioinfo.py <cache_file> -showall\n\
 ./getradioinfo.py <cache_file> -search <text>\n\
 ./getradioinfo.py <cache_file> -delete <id>\n")

rcomm = rcomm.rstrip(",")

class RadioDB():
    """ Used to store persistent data (self.db) """
    def __init__(self):
        self.db_file = rfile
        self.db = dict()
        self.load()

    def load(self):
        # Sets self.db
        with open(self.db_file, "r") as f:
            self.db = pickle.load(f)

    def dump(self):
        # Writes self.db to self.db_file
        with open(self.db_file, "w") as f:
            pickle.dump(self.db, f)

x = RadioDB()
try:
    rid = sys.argv[3]
except IndexError:
    print("Warning: Argument 3 not provided")
    pass

if rfile == "eradio.cache.db":
    url_main = "http://www.e-radio.gr/player/mini.asp?c=000&pt=1&ppt=2&sid="
elif rfile == "24radio.cache.db":
    url_main = "http://www.24radio.gr/code/station.php?station_id="

#Functions
try:
    if rcomm == "-showall":
        for k, v in x.db.iteritems():
            print(k)
            print(v["title"].encode("utf-8"))
            print("ID: {0}".format(v["id"]))
            print("Link: {0}{1}".format(url_main, v["id"]))
            try:
                print(v["url"])
            except:
                print("NO URL (or not processed yet)")
                pass
            print("\n")
    elif rcomm == "-show":
        pprint.pprint(x.db[rid])
        print("Link: {0}{1}".format(url_main, rid))
    elif rcomm == "-delete":
        x.db.pop(rid)
        print("Radio id %s removed" % (rid))
except IndexError:
    pass

x.dump()

