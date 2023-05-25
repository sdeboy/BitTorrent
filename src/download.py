import random, string, socket, struct, asyncio
import torrent, peer, message
from tracker import announce
import math, hashlib, time
# main logic that manages connections with peers

# max numbers of bytes that we can request from a given peer
MAX_BYTES = 16384
peers_returned = 0

async def start(torrent, manager, download, my_id, port):
    # Repeatedly get peers and talk to them, until the download is done
    # If we fail to get all the pieces, this should eventually ask the 
    # tracker for a new set of peers(?)
    while not manager.download_done():
        # required to print # peers returned
        global peers_returned
        peers_returned = 0
        
        # print address
        print("torrent address:")
        print(torrent.announce)
        # get and print PeerData
        print("\npeers:")
        peer_data = announce(torrent, my_id, 0, 0, torrent.info.length, compact, "started", port)
        print(peer_data)
        
        # connect to peers
        # SWITCH TO TASKGROUP METHOD
        tasks = []
        for peer in peer_data.peers:
            tasks.append(asyncio.create_task(handle_peer(peer,torrent,my_id,manager,download_file, endgame)))
        #await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.gather(*tasks, return_exceptions=False)
        
    print(f"{} DOWNLOADED AT {}", download.name,
          os.path.dirname(os.path.abspath(download.name)))
    
async def handle_peer(peer, torrent, my_id, manager, download_file, endgame):
    # TODO: consider potential errors with peers not responding
    try:
        await peer.connect()
        await peer.handshake(torrent.info_hash, my_id)
    except:
        print("failed intro")
        return
    print("done intro")

    MAX_BLOCKS = math.ceil(torrent.info.piecelength//MAX_BYTES)
    blocks_received = 0
    blocks = [0]*MAX_BLOCKS
    requesting_piece = -1
    
    print("entering main loop")
    while True:
        if requesting_piece != -1 and manager.have_piece(requesting_piece):
            print("OTHER PEER HAS DOWNLOADED, CANCELLING")
            await peer.send_cancel()
            requesting_piece = -1
        if manager.download_done():
            print("DOWNLOAD DONE, RETURNING")
            await peer.close()
            print("done closing writer")
            global peers_returned
            peers_returned += 1
            print("PEERS RETURNED: " + str(peers_returned))
            return

        # wait for message
        try:
            msg = await asyncio.wait_for(peer.read_msg(), timeout=5.0)
        except ConnectionError:
            return
        except Exception:
            continue
                        
        print(str(msg) + f" from {peer.peer_id}")
        match msg.message_type:
            case 'CHOKE':
                peer.choked = True
            case 'UNCHOKE':
                peer.choked = False
            case 'INTERESTED':
                peer.interested = True
            case 'NOT_INTERESTED':
                peer.interested = False
            case 'BITFIELD':
                peer.bitmap_received = True
                manager.add_peer(peer.peer_id, msg.bitfield)
                print(f'sending interested to {peer.peer_id}')
                await peer.send_interested()
            case 'REQUEST':
                # TODO: call seeder function
                print("TODO: REQUEST")
            case 'HAVE':
                manager.update_peer(peer.peer_id, msg.piece_index)
            case 'PIECE':
                blocks[msg.begin//MAX_BYTES] = msg.block
                blocks_received += 1
                
                if (blocks_received == MAX_BLOCKS):
                    piece = b"".join(blocks)

                    # verify step
                    i = (requesting_piece*20)
                    realhash = torrent.info.pieces[i:i+20]
                    sha1 = hashlib.sha1()
                    sha1.update(piece)
                    ourhash = sha1.digest()
                    # write step if verified, else put back in queue
                    if (ourhash == realhash):
                        print("hashes match, writing to file")
                        await write(download_file, requesting_piece*torrent.info.piecelength, piece)
                        manager.downloaded_piece(requesting_piece)
                    else:
                        # TODO: put back in queue
                        manager.return_to_queue(requesting_piece)
                    # reset trackers
                    blocks_received = 0
                    requesting_piece = -1
            case 'CANCEL':
                # can be ignored?
                # will be tricky as cancels currently
                # sending message?
                print("TODO: CANCEL")
            case 'PORT':
                print("TODO: PORT")
                # think this is not relevant for how protocol
            case _:
                print('UNKNOWN MESSAGE')

        if peer.choked == False and peer.bitmap_received == True and requesting_piece == -1:
            print("preparing to request")
            block_info = manager.next_request(peer.peer_id)

            in_endgame = False
            
            if (block_info == -1 or block_info == None):
                if endgame:
                    in_endgame = True
                    print("ENTERING THE ENDGAME")
                    block_info = manager.get_random_pending()
                    print("GOT RANDOM PENDING")
                    if block_info == None or block_info == -1:
                        print("NO PENDING AVAILABLE")
                        return
                else:
                    continue
                
                
            print(f"requesting piece {block_info} from peer {peer.peer_id}")
            try:
                await peer.send_request(block_info, torrent.info.piecelength) # index and length, offset calculated later
            except:
                if not in_endgame:
                    manager.return_to_queue(block_info)
                    continue
            requesting_piece = block_info
            print("request sent")
            # send request, use message.py maybe          


# TODO: writes to path
async def write(download_file, piece_location, piece):
    print(f"WRITING to {piece_location}")
    download_file.seek(piece_location)
    download_file.write(piece)

# reads chunk from file
# TODO: fix bugs
def retrieve_chunk(download_file, start, end):
    loc = download_file.seek(start)
    return download_file.read(end)
