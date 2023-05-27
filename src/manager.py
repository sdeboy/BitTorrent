import asyncio, random, copy
# tracks download file information

class Manager:
    def __init__(self, torrent, download_file):
        # general torrent info
        self.torrent = torrent
        self.download_file = download_file
        self.total_pieces = len(torrent.info.pieces)//20
        # bit fields
        self.peer_bitfield = {}
        self.our_bitfield = [False]*self.total_pieces
        # queue of acquired pieces to later send
        self.have_msg_list = {}
        # holds information on pieces to download
        self.pending_pieces = []
        self.queue = list(zip([0]*self.total_pieces,
                          range(self.total_pieces)))
        # how much has been downloaded/uploaded
        self.uploaded = 0
        self.downloaded = 0
        self.left = torrent.info.length

    # add peer have_msg dict
    def add_peer(self, peer_id):
        self.have_msg_list[peer_id] = []
        
    # delete peer from dict
    def remove_peer(self, peer_id):
        if peer_id in self.peer_bitfield:
            del self.peer_bitfield[peer_id]
        if peer_id in self.have_msg_list:
            del self.have_msg_list[peer_id]

    # Updating in response to Have message
    def update_peer(self, peer_id, index):
        if peer_id in self.peer_bitfield:
            self.peer_bitfield[peer_id][index] = True

    # add bitfield to peer
    def add_bitfield(self, peer_id, bitfield):
        self.peer_bitfield[peer_id] = bitfield
        for i, bit in enumerate(bitfield):
            for j, pair in enumerate(self.queue):
                if i == pair[1]:
                    self.queue[j] = (self.queue[j][0]+1,
                                     self.queue[j][1])
                    continue
        self.queue.sort(key=lambda i:(i[0],
                                      random.randrange(64)))
        
    # add newly downloaded to have message lists
    def add_to_have_list(self, index):
        for k, v in self.have_msg_list.items():
            v.append(index)
        
    # get have message list
    def get_have_list(self, peer_id):
        try:
            have_list = self.have_msg_list[peer_id]
            self.have_msg_list = []
            return have_list
        except:
            return []

    def get_random_pending(self):
        try:
            return random.choice(self.pending_pieces)[1]
        except:
            return None
            
    # determine what the next request will be for given peer
    def next_request(self, peer_id):
        try:
            for i, piece in enumerate(self.queue):
                if self.peer_bitfield[peer_id][piece[1]]:
                    self.pending_pieces.append(piece)
                    return self.queue.pop(i)[1]
            return -1
        except: 
            print("error with piece queue")

    def return_to_queue(self, index):
        piece = self.remove_from_pending_list(index)
        if piece:        
            self.queue.append(piece)
            
    async def write_piece(self, piece, index):
        if not self.our_bitfield[index]:
            try:
                self.download_file.seek(index*self.torrent.info.piecelength)
                self.download_file.write(piece)
                self.our_bitfield[index] = True
                self.downloaded += len(piece)
                self.left -= len(piece)
                self.add_to_have_list(index)
            except:
                print("error writing piece")
                return
            try:
                self.remove_from_pending_list(index)
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
        return self.our_bitfield[val]
        
    def download_done(self):
        if self.left == 0:
            return True
        return False

    def remove_from_pending_list(self, index):
        for piece in self.pending_pieces:
            if piece[1] == index:
                self.pending_pieces.remove(piece)
                return piece
        return None

    
    # gives percentage of download done
    def progress(self):
        return sum(self.our_bitfield)/self.total_pieces

