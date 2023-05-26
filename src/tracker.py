import bencode, socket, requests, logging
from peer import PeerData, Peer

# this file handles communication with tracker list
def announce(torrent, peer_id, uploaded, downloaded, left, event, port):
    # construct args for http request
    params = locals()
    del params['torrent']
    params['info_hash'] = torrent.info_hash
    params['compact'] = 1

    # send request and create peer list from it
    res = requests.get(torrent.announce, params=params)
    return PeerData(bencode.decode(res.content))
