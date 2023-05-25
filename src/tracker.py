import bencode, socket, requests
from peer import PeerData, Peer

# this file handles communication with tracker list
def announce(announce, info_hash, peer_id, uploaded, downloaded, left, event, port):
    # construct http get request
    params = {}
    for key, val in locals():
        if key != '__announce__':
            params[key[2:-2]] = val
    print(params)
    peer_res = requests.get(announce, params=params)
    # PeerData constructs list from response
    return PeerData(bencode.decode(peer_res))
