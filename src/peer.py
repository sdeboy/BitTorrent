import bencode, asyncio, struct, asyncio
import message
# this file manages structures to hold peer data

# 2^14 is max byte amount that can be requested
MAX_BYTES = 16384

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
        self.choked = True
        self.interested = False
        self.reader = None
        self.writer = None
        self.throughput = 0
        self.bitmap_received = False
        
    def __str__(self):
        return "  peer: "+str(self.ip)+":"+str(self.port) + "\n"

    # attempts to make connection with peer
    async def connect(self):
        print("connecting to "+str(self.ip)+":"+str(self.port))
        t = asyncio.open_connection(self.ip, self.port)
        try:
            self.reader, self.writer = await asyncio.wait_for(t, timeout=10)
        except:
            raise
        print("connected to "+str(self.ip)+":"+str(self.port))

    # attempts to send handshake with peer
    async def handshake(self, info_hash, peer_id):
        handshake = struct.pack("!B19s8s20s20s", 19, b"BitTorrent protocol",
                                b"\x00"*8, info_hash, bytes(peer_id, 'utf-8'))
        try:
            await self.write(handshake)
            r = await self.readexactly(68)            
        except:
            raise
        # TODO: verify fields appropriately
        pstrlen, pstr, reserved, info_hash, self.peer_id = struct.unpack(
            "!B19s8s20s20s", r)        

    # closes connection
    async def close(self):
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except:
            print("error during close")
            
    # reads next incoming message
    async def read_msg(self):
        try:
            msg_len: int = 0
            while msg_len == 0:
                msg_len = int.from_bytes(await reader.readexactly(4), "big")
            msg: bytes = await self.readexactly(msg_len)
            return message.class_from_bytes(msg)
        except:
            raise

    # send message class
    async def send_msg(self, msg):
        try:
            await self.write(msg.get())
            await self.write(msg.get_extra())
        except:
            raise

    # various message types to send
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
        
    async def send_request(self, index, length):
        offset = 0
        try:
            while offset < length:
                chunk_size = min(MAX_BYTES, length - offset)
                msg = message.RequestMessage(index, offset, chunk_size)
                await self.send_msg(msg)
                offset += chunk_size
        except:
            print("Error sending piece requests")
            raise


    # basic wrappers for reader/writer
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

def generate_list(peer_data):
    if isinstance(peer_data, bytes):
        return [Peer(peer_data[6*x:6*x+6]) for x in range(int(len(peer_data) / 6))]
    else:
        list = []
        for i in range(len(peer_data)):
            list.append(Peer(peer_data[i]))
        return list

def peer_list_str(list):
    s = ""
    for i in range(len(list)):
        s += str(list[i])
    return s