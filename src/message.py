from typing import List
import struct
# interpret bytestream to messages and the converse

MESSAGE_TYPES: List[str] = [
    'CHOKE','UNCHOKE','INTERESTED','NOT_INTERESTED',
    'HAVE','BITFIELD','REQUEST','PIECE','CANCEL','PORT'
]

class Message:
    def __init__(self, msg_type: str):
        self.msg_type = msg_type
        self.length_prefix = 1
    def __str__(self):
        return "MESSAGE TYPE:"+str(self.msg_type)
    def get_extra(self): # to be overridden
        return b""
    def get(self):
        msg_id: int = MESSAGE_TYPES.index(self.msg_type)
        return struct.pack("!IB", self.length_prefix, msg_id)

class HaveMessage(Message):
    def __init__(self, piece_index: int):
        super().__init__('HAVE')
        self.piece_index: int = piece_index
        self.length_prefix: int = 5
    def __str__(self):
        return super().__str__()+f", INDEX: {self.piece_index}"
    def get_extra(self):
        return struct.pack("!I", self.piece_index)

class BitfieldMessage(Message):
    def __init__(self, bits: bytes):
        super().__init__('BITFIELD')
        self.bitfield: List[bool] = [(byte & (1<<(7-bit))) > 0 for byte in bits for bit in range(8)]
        self.length_prefix: int = 1 + len(bits)
    def __str__(self):
        return super().__str__()
    
class RequestMessage(Message):
    def __init__(self, index: int, begin: int, length: int):
        super().__init__('REQUEST')
        self.index: int = index
        self.begin: int = begin
        self.length: int = length
        self.length_prefix: int = 13
    def __str__(self):
        return super().__str__()+f", INDEX: {self.index}, BEGIN {self.begin}, LENGTH {self.length}"
    def get_extra(self):
        return struct.pack("!III", self.index, self.begin, self.length)
        
class CancelMessage(Message): # Request and cancel have same format
    def __init__(self, index: int, begin: int, length: int):
        super().__init__('CANCEL')
        self.index: int = index
        self.begin: int = begin
        self.length: int = length
    def __str__(self):
        return super().__str__()
    def get_extra(self):
        return struct.pack("!III", self.index, self.begin, self.length)

class PieceMessage(Message):
    def __init__(self, index: int, begin: int, block: bytes):
        super().__init__('PIECE')
        self.index: int = index
        self.begin: int = begin
        self.block: bytes = block
        self.length_prefix: int = 9 + len(block)
    def __str__(self):
        return super().__str__()+f", INDEX: {self.index}, BEGIN {self.begin}"
    def get_extra(self):
        return struct.pack("!II", self.index, self.begin)

class PortMessage(Message):
    def __init__(self, port: int):
        super().__init__('PORT')
        self.port: int = port
    def __str__(self):
        return super().__str__()
    def get_extra(self):
        return struct.pack("!H", self.port)

def class_from_bytes(msg: bytes, msg_len: int) -> Message:
    msg_id: int = int(msg[0])
    msg_type: str = MESSAGE_TYPES[msg_id]
    
    # unknown id
    if not (msg_id >= 0 and msg_id <= len(MESSAGE_TYPES)):
        print("ERROR: DO NOT RECOGNIZE ID: " + str(msg_id))
        raise

    # no extra data
    if msg_type in ['CHOKE', 'UNCHOKE', 'INTERESTED', 'NOT_INTERESTED']:
        return Message(msg_type)
    
    # Have contains a piece index
    if msg_type == 'HAVE':
        _, piece_index = struct.unpack("!BI", msg)
        return HaveMessage(piece_index)
    
    # Bitfield
    if msg_type == 'BITFIELD':
        return BitfieldMessage(msg[1:])
    
    # Request
    if msg_type == 'REQUEST':
        _, index, begin, length = struct.unpack("!BIII", msg)
        return RequestMessage(index, begin, length)
    
    # Piece
    if msg_type == 'PIECE':
        _, index, begin, block = struct.unpack("!BII"+str(msg_len-9)+"s", msg)
        return PieceMessage(index, begin, block)
    
    # Cancel, same format as request, different type output
    if msg_type == 'CANCEL':
        _, index, begin, length = struct.unpack("!BIII", msg)
        return CancelMessage(index, begin, length)
    
    # Port
    if msg_type == 'PORT':
        _, port_number = struct.unpack("!BH", msg)
        return PortMessage(port_number)
