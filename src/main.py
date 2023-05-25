#!/usr/bin/env python
# takes and processes the file input for main logic

import sys, bencode, asyncio, random, string, os, socket
import torrent, manager
from manager import Manager
from download import start

# id to identify ourselves
my_id = ''.join(random.choice(string.ascii_letters)
                      for i in range(20))
# port to use while seeding/leeching
port = get_free_port()
# command line parameters 
torr_path = sys.argv[1]
download_path = sys.argv[2]

# interpret .torrent file and create our file manager
torrent
with open(torr_path, 'rb') as torrent_file:
        torrent = Torrent(bencode.decode(torrent_file.read()))
manager = Manager(torrent)

# make directory and file from parameter
if not os.path.exists(download_path):
        os.makedirs(download_path)
download = open(download_path+"/"+torrent.info.name, '+b')

# start torrent program with given parameters
asyncio.run(start(torrent, manager, download, my_id, port))

# return a free port
def get_free_port():
        sock = socket.socket()
        sock.bind(('', 0))
        return sock.getsockname()[1]
