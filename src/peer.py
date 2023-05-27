import bencode, asyncio, struct, asyncio
import message
# this file manages structures to hold peer data

# 2^14 is max byte amount that can be requested
MAX_BYTES = 16384

# PeerData/Peer based off dict from bencode
class PeerData:
    def __init__(self, response):
            self.interval = response['interval']
            self.peers = generate_list(response['peers'])
    def __str__(self):
        return "response:\n  interval: "+str(self.interval)+"\n"+peer_list_str(self.peers)

class Peer:
    def __init__(self, peer):
        self.ip = peer['ip'] if isinstance(peer, dict) else '.'.join(str(c) for c in peer[0:4])
        self.port = peer['port'] if isinstance(peer, dict) else int(peer[4]) << 8 | int(peer[5])
        self.peer_id = None
        self.peer_choked = True
        self.my_choked = True
        self.interested = False
        self.reader = None
        self.writer = None
        self.throughput = 0
        self.bitmap_received = False
        
    def __str__(self):
        return "  peer: "+str(self.ip)+":"+str(self.port) + "\n"

    # attempts to make connection with peer
    async def connect(self):
        t = asyncio.open_connection(self.ip, self.port)
        try:
            self.reader, self.writer = await asyncio.wait_for(t, timeout=10)
        except:
            raise

    # closes connection
    async def close(self):
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except:
            print("error during close")
            raise            

    # attempts to send handshake with peer
    async def handshake(self, info_hash, peer_id):
        handshake = struct.pack("!B19s8s20s20s", 19, b"BitTorrent protocol",
                                b"\x00"*8, info_hash, bytes(peer_id, 'utf-8'))
        try:
            await self.write(handshake)
            r = await self.readexactly(68)            
        except:
            raise
        _, _, _, _, self.peer_id = struct.unpack(
            "!B19s8s20s20s", r)
        
    # reads next incoming message
    async def read_msg(self):
        try:
            msg_len = 0
            while msg_len == 0:
                msg_len = int.from_bytes(await self.reader.readexactly(4), "big")
            msg = await self.readexactly(msg_len)
            return message.class_from_bytes(msg, msg_len)
        except:
            raise

    # send the given Message class
    async def send_msg(self, msg):
        try:
            await self.write(msg.get())
            await self.write(msg.get_extra())
        except:
            raise

    # message types to send
    async def send_interested(self):
        try:
            await self.send_msg(message.Message('INTERESTED'))
        except:
            raise
        
    async def send_cancel(self):
        try:
            await self.send_msg(message.Message('CANCEL'))
        except:
            raise
        
    async def send_have(self, index):
        try:
            await self.send_msg(message.HaveMessage(index))
        except:
            raise

    async def send_request(self, index, length):
        offset = 0
        try:
            # must request piece in 2^14 size blocks
            while offset < length:
                chunk_size = min(MAX_BYTES, length - offset)
                msg = message.RequestMessage(index, offset, chunk_size)
                await self.send_msg(msg)
                offset += chunk_size
        except:
            raise

    async def send_piece(self, index, offset, block):
        try:
            await self.send_msg(
                message.PieceMessage(index, offset, block))
        except:
            raise
        

    # wrappers for reader/writer
    async def write(self, msg):
        try:
            self.writer.write(msg)
            await self.writer.drain()
        except:
            raise

    async def readexactly(self,len):
        try:
            return await self.reader.readexactly(len)
        except:
            raise
        
# # # # # # # # # # #
# HELPER  FUNCTIONS #
# # # # # # # # # # #

# generates list from the http response
def generate_list(peer_data):
    if isinstance(peer_data, bytes):
        return [Peer(peer_data[6*x:6*x+6]) for x in range(int(len(peer_data)/6))]
    else:
        list = []
        for i in range(len(peer_data)):
            list.append(Peer(peer_data[i]))
        return list

# helps print the peer list
def peer_list_str(list):
    s = ""
    for i in range(len(list)):
        s += str(list[i])
    return s
