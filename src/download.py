import random, string, socket, struct, asyncio
import torrent, peer, message
from tracker import announce
import math, hashlib, time
# main logic that manages connections with peers

# maximum bytes that can be requested from a peer
MAX_BYTES = 16384

# get peers sends to handle_peer until download is done
async def start(torrent, manager, my_id, port):
    # request new peerlist if existing one is not working
    while not manager.download_done():
        # print address
        print(f"downloading from: {torrent.announce}")
        print(torrent.announce)
        peers = announce(torrent, my_id, 0, 0,
                         torrent.info.length, "started", port)
        
        # connect to each peer and follow protocol
        tasks = [asyncio.create_task(progress(manager))]
        for peer in peers.peers:
            tasks.append(asyncio.create_task(handle_peer(
                peer, torrent, my_id, manager)))
        await asyncio.gather(*tasks, return_exceptions=False)
    # done
    peers = announce(torrent, my_id, 0, torrent.info.length,
                     0, "stopped", port)
    print("download complete")

# print progress message intermittently
async def progress(manager):
    print("starting download")
    while not manager.download_done():
        await asyncio.sleep(1)
        # print(f"progress: {manager.progress()}", end='\r')
    print()
    

# bittorrent protocol for each peer
async def handle_peer(peer, torrent, my_id, manager):
    # attempts connection
    try:
        await peer.connect()
        await peer.handshake(torrent.info_hash, my_id)
    except:
        return

    # variables to track blocks of each piece
    MAX_BLOCKS = math.ceil(torrent.info.piecelength//MAX_BYTES)
    blocks_received = 0
    blocks = [0]*MAX_BLOCKS
    requesting = -1

    while True:
        # if piece downloaded from another peer, cancel request
        if requesting != -1 and manager.have_piece(requesting):
            await peer.send_cancel()
            requesting = -1
        # if file has finished downloading, return
        if manager.download_done():
            await peer.close()
            return

        # wait for message
        try:
            msg = await asyncio.wait_for(peer.read_msg(), timeout=5.0)
        except ConnectionError:
            # issue with connection case
            return
        except Exception:
            # timeout case
            continue
        print(f"got message {msg}")
        
        match msg.msg_type:
            case 'CHOKE':
                peer.my_choked = True
            case 'UNCHOKE':
                peer.my_choked = False
            case 'INTERESTED':
                peer.interested = True
                peer.peer_choked = False
            case 'NOT_INTERESTED':
                peer.interested = False
                peer.peer_choked = True
            case 'BITFIELD':
                peer.bitmap_received = True
                manager.add_peer(peer.peer_id, msg.bitfield)
                await peer.send_interested()
            case 'REQUEST':
                if not my_choked and manager.have_piece(msg.piece_index):
                    block = await manager.read_block(msg.piece_index,
                                                     msg.block_offset, msg.length)
                    try:
                        await peer.send(PieceMessage(msg.piece_index,
                                                     msg.block_offset, block))
                    except:
                        print("error sending block to client")
                        continue        
            case 'HAVE':
                manager.update_peer(peer.peer_id, msg.piece_index)
            case 'PIECE':
                # received another block of the piece
                blocks[msg.begin//MAX_BYTES] = msg.block
                blocks_received += 1
                # have all blocks of the piece
                if (blocks_received == MAX_BLOCKS):
                    piece = b"".join(blocks)
                    # verify step
                    i = (requesting*20)
                    realhash = torrent.info.pieces[i:i+20]
                    sha1 = hashlib.sha1()
                    sha1.update(piece)
                    ourhash = sha1.digest()
                    # write step if verified, else put back in queue
                    if ourhash == realhash:
                        await manager.write_piece(piece, requesting)
                    else:
                        manager.return_to_queue(requesting)
                    # reset tracker varibles
                    blocks_received = 0
                    requesting = -1
            case _:
                print('OTHER MESSAGE')

        # send piece request if we meet requirements
        if (not peer.my_choked) and peer.bitmap_received and requesting == -1:
            block_info = manager.next_request(peer.peer_id)                 
            # if no piece in queue, request from pending list
            if block_info == -1 or block_info == None:
                block_info = manager.get_random_pending()
                if block_info == None or block_info == -1:
                    continue
            # send request
            try:
                await peer.send_request(block_info, torrent.info.piecelength)
            except:
                manager.return_to_queue(block_info)
                continue                                        
            # update piece being requested for book-keeping
            requesting = block_info
