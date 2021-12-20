import struct
import numpy as np
class BufferDecoder(object):
    def __init__(self,bytes) -> None:
        self.bytes=bytes
        self.curr=0
        
    def read_var_int32(self):
        v_=self.read_uint32()
        v= np.int32(v_>>1)
        if (v_&1)!=0:
            v=~v
        return int(v)
            
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
    def read_var_uint64(self):
        # 我nm真的有必要为了几个比特省到这种地步吗??uint32最多也就5个比特吧??
        i,v=0,0 
        while i<70:
            b=self.read_byte()
            v|=(b&0x7f)<<i
            if b&0x80==0:
                return v
            i+=7
        assert False,f'read_var_uint64 fail i:{i} v:{v} {self}'

    def read_vec3(self):
        self.curr+=12
        return struct.unpack('fff',self.bytes[self.curr-12:self.curr])
    def read_float32(self):
        self.curr+=4
        return struct.unpack('f',self.bytes[self.curr-4:self.curr])[0]
    
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
        return bytes
    def read_UUID(self):
        self.curr+=16
        uuid_bytes=self.bytes[self.curr-16:self.curr]
        return self.reverseUUIDBytes(uuid_bytes)
    def read_int32(self):
        self.curr+=4
        return struct.unpack('i',self.bytes[self.curr-4:self.curr])[0]
    def read_uint32(self):
        self.curr+=4
        return struct.unpack('I',self.bytes[self.curr-4:self.curr])[0]
    
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
        es=s.encode(encoding='utf-8')
        self.write_var_uint32(len(es))
        self.append(es)
    
    def write_UUID_bytes(self,uuid_bytes:bytes):
        self.append(uuid_bytes)
        