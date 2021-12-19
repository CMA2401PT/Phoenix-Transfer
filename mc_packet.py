from os import write
import struct
from typing import List
from dataclasses import dataclass

# only a very small part of packets...
# go to fb/minecraft/protocol/packet/pool.go for full list

IDLogin=1
IDText=9 
IDCommandRequest=77
IDCommandOutput=79

class BufferDecoder(object):
    def __init__(self,bytes) -> None:
        self.bytes=bytes
        self.curr=0
    def read_var_uint32(self):
        # 我nm真的有必要为了几个比特省到这种地步吗??uint32最多也就5个比特吧??
        i,v=0,0 
        while i<35:
            b=self.read_byte()
            v|=(b&0x7f)<<i
            if b&0x80==0:
                return v
            i+=7
        assert False,f'read_var_uint32 fail i:{i} v:{v} {self}'
    def read_tail(self):
        return self.bytes[self.curr:]
    def read_byte(self):
        self.curr+=1
        return struct.unpack('B',self.bytes[self.curr-1:self.curr])[0]
    def read_boolen(self):
        return self.read_byte()==1
    def read_str(self):
        length=self.read_var_uint32()
        self.curr+=length
        return self.bytes[self.curr-length:self.curr].decode(encoding='utf-8')
    @staticmethod
    def reverseUUIDBytes(bytes):
        bytes[8:]+bytes[:8]
        return bytes[::-1]
    def read_UUID(self):
        self.curr+=16
        uuid_bytes=self.bytes[self.curr-16:self.curr]
        return self.reverseUUIDBytes(uuid_bytes)

class BufferEncoder(object):
    def __init__(self) -> None:
        self._bytes_elements=[]
        self._bytes_elements_count=0
        self._bytes=b''
    
    @property
    def bytes(self):
        if len(self._bytes_elements)!=self._bytes_elements_count:
            self._bytes+=b''.join(self._bytes_elements[self._bytes_elements_count:])
            self._bytes_elements_count=len(self._bytes_elements)
        return self._bytes
    
    def append(self,bs:bytes):
        self._bytes_elements.append(bs)
    
    def write_byte(self,b):
        self.append(struct.pack('B',b))
    
    def write_boolen(self,b:bool):
        self.append(struct.pack('B',b))
    
    def write_var_uint32(self,x):
        while x>=0x80:
            self.write_byte(x|0x80)
            x>>=7
        self.write_byte(x)

    def write_str(self,s:str):
        self.write_var_uint32(len(s))
        self.append(s.encode(encoding='utf-8'))
    
    def write_UUID_bytes(self,uuid_bytes:bytes):
        self.append(uuid_bytes)
        





# Login 
@dataclass
class Login:
    ClientProtocol:int
    ConnectionRequest:bytes
    
def decode_login(d:BufferDecoder):
    return Login(d.read_var_uint32(),d.read_tail())

# Chat 
TextTypeChat, TextTypeWhisper, TextTypeAnnouncement=1,7,8
TextTypeRaw, TextTypeTip, TextTypeSystem, TextTypeObject, TextTypeObjectWhisper=0,5,6,9,10
TextTypeTranslation, TextTypePopup, TextTypeJukeboxPopup=2,3,4

@dataclass
class Text:
    TextType:int=0
    NeedsTranslation:bool=False
    SourceName:str=''
    Message:str =''
    Parameters:str =''
    XUID:str=''
    PlatformChatID:str=''

def decode_text(d:BufferDecoder):
    o=Text()
    TextType,NeedsTranslation= int(d.read_byte()),d.read_boolen()
    o.TextType=TextType
    o.NeedsTranslation=NeedsTranslation
    if TextType in [TextTypeChat, TextTypeWhisper, TextTypeAnnouncement]:
        o.SourceName=d.read_str()
        o.Message=d.read_str()
    elif TextType in [TextTypeRaw, TextTypeTip, TextTypeSystem, TextTypeObject, TextTypeObjectWhisper]:
        o.Message=d.read_str()
    elif TextType in [TextTypeTranslation, TextTypePopup, TextTypeJukeboxPopup]:
        o.Message=d.read_str()
        length=d.read_var_uint32()
        o.Parameters=[d.read_str() for _ in range(length)]
    o.XUID=d.read_str()
    o.PlatformChatID=d.read_str()
    return o

# CommandOrigin
CommandOriginPlayer=0
CommandOriginDevConsole=3
CommandOriginTest=4
CommandOriginAutomationPlayer=5

@dataclass
class CommandOrigin:
    Origin:int=0
    UUID:bytes=b''
    RequestID:str=''
    PlayerUniqueID:int=0

def decode_command_origin_data(d:BufferDecoder):
    o=CommandOrigin()
    o.Origin=d.read_var_uint32()
    o.UUID=d.read_UUID()
    o.RequestID=d.read_str()
    if o.Origin in [CommandOriginDevConsole,CommandOriginTest]: 
        o.PlayerUniqueID=d.read_var_uint32()
    return o

def encode_command_origin_data(e:BufferEncoder,i:CommandOrigin):
    e.write_var_uint32(i.Origin)
    e.write_UUID_bytes(i.UUID)
    e.write_str(i.RequestID)
    if i.Origin == CommandOriginDevConsole or i.Origin == CommandOriginTest:
        e.write_var_uint32(i.PlayerUniqueID)

# CommandOutputMessage
@dataclass
class CommandOutputMessage:
    Success:bool=False
    Message:str =''
    Parameters:List[str]=None
    
def decode_command_message(d:BufferDecoder):
    o=CommandOutputMessage()
    o.Success=d.read_boolen()
    o.Message=d.read_str()
    count=d.read_var_uint32()
    o.Parameters=[d.read_str() for _ in range(count)]
    return o

# CommandOutput
@dataclass
class CommandOutput:
    CommandOrigin:CommandOrigin=None
    OutputType:int=0
    SuccessCount:int=0
    OutputMessages:List[CommandOutputMessage]=None
    UnknownString:str=''

def decode_command_output(d:BufferDecoder):
    o=CommandOutput()
    o.CommandOrigin=decode_command_origin_data(d)
    o.OutputType=int(d.read_byte())
    o.SuccessCount=d.read_var_uint32()
    count=d.read_var_uint32()
    o.OutputMessages=[decode_command_message(d) for _ in range(count)]
    if o.OutputType==4:
        o.UnknownString=d.read_str()
    return o

#CommandRequest
@dataclass
class CommandRequest:
    CommandLine:str=''
    CommandOrigin:CommandOrigin=None
    Internal:bool=False
    UnLimited:bool=False

def encode_command_request(e:BufferEncoder,i:CommandRequest):
    e.write_str(i.CommandLine)
    encode_command_origin_data(e,i.CommandOrigin)
    e.write_boolen(i.Internal)
    e.write_boolen(i.UnLimited)
    return e

packet_encode_pool={
    IDCommandRequest:encode_command_request
}

packet_decode_pool={
    IDLogin:decode_login,
    IDText:decode_text,
    IDCommandOutput:decode_command_output,    
}