import asyncio, random
# tracks download file information
class Manager:
    def __init__(self, torrent, download_file):
        self.torrent = torrent
        self.download_file = download_file
        self.download_complete = False
        self.peer_bitfield = {}
        self.total_pieces = len(torrent.info.pieces)//20
        self.our_bitfield = bytearray(self.total_pieces)
        self.pending_pieces = []
        self.queue = list(range(self.total_pieces))
        self.uploaded = 0
        self.downloaded = 0
        self.left = torrent.info.length

    # add peer to dict
    def add_peer(self, peer_id, bitfield):
        self.peer_bitfield[peer_id] = bitfield

    # delete peer from dict
    def remove_peer(self, peer_id):
        if peer_id in self.peer_bitfield:
            del self.peer_bitfield[peer_id]

    # Updating in response to Have message
    def update_peer(self, peer_id, index):
        if peer_id in self.peer_bitfield:
            self.peer_bitfield[peer_id].add_piece(index)

    def get_random_pending(self):
        try:
            return random.choice(self.pending_pieces)
        except:
            return None
            
    # determine what the next request will be for given peer
    def next_request(self, peer_id):
        try:
            for i, piece_num in enumerate(self.queue):
                if self.peer_bitfield[peer_id].has_piece(piece_num):
                    self.pending_pieces.append(self.queue[i])
                    return self.queue.pop(i)
            return -1
        except: 
            print("error with piece queue")

    def return_to_queue(self, index):
        try:
            self.pending_pieces.remove(val)
        except:
            return
        self.queue.append(index)

    async def write_piece(self, piece, index):
        if self.our_bitfield[index] != 1:
            try:
                self.download_file.seek(index*self.torrent.info.piecelength)
                self.download_file.write(piece)
                self.our_bitfield[index] = 1
                self.downloaded += len(piece)
                self.left -= len(piece)
            except:
                print("error writing piece")
                return
            try:
                self.pending_pieces.remove(index)
            except:
                return

    async def read_block(self, index, offset, length):
        start = index*self.torrent.info.piecelength+offset
        end = start+length
        try:
            await self.download_file.seek(start)
            self.uploaded += length
            return await self.download_file.read(end)
        except:
            print("error reading file")
        
    def have_piece(self, val):
        if (self.our_bitfield[val] == 1):
            return True
        return False
        
    def download_done(self):
        if self.download_complete:
            return True
        for i in self.our_bitfield:
            if i == 0:
                return False
        self.download_complete = True
        return True

    # gives percentage of download done
    def progress(self):
        return sum(self.our_bitfield)/self.total_pieces
        
