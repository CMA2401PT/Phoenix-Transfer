import socket
from uuid import uuid1,UUID
from queue import Queue, Empty
from threading  import Thread
import struct
import mc_packet as mcp

BUFFER_SIZE=2*12

def connect_to_fb_transfer(host="localhost",port=8000):
    '''python 作为server端，需要某种手段建立和fb的链接'''
    addr = (host,port)
    proxy = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    print(f'Try connecting to @ {addr} ...')
    proxy.connect(addr)
    return proxy

'''
    从这里开始，是各种处理接收的函数，
    你问我为啥用这种注释？
    因为在vscode里是很醒目的绿色
'''

def prase_msg(msg:bytes):
    '''将字节形式的收到的数据包解析为特定mc类型'''
    d=mcp.BufferDecoder(msg)
    value=d.read_var_uint32()
    packet_id = value & 0x3FF
    sender_subclient=(value >> 10) & 0x3
    target_subclient=(value >> 12) & 0x3
    decode_func=mcp.packet_decode_pool.get(packet_id)
    if decode_func is None:
        # print(f'decode func not implemented: packet type id: {packet_id}')
        # print(f'forward: fb -> packet(ID={packet_id}) -> drop')
        pass 
    else:
        print(f'forward: fb -> packet(ID={packet_id}) -> decode:')
        decoded_msg=decode_func(d)
        print(str(decoded_msg))
        return decoded_msg


'''
    从这里开始，是各种处理发送的函数，
    你问我为啥用这种注释？
    同上
'''

def send_msg(conn:socket.socket,msg:bytes):
    '''我们需要这个函数来为待发送的数据添加一个简单的头(指示数据包的大小),并发送出去'''
    msg_len=len(msg)+4
    full_msg=struct.pack('I',msg_len)+msg
    current_send=0
    while current_send<msg_len:
        current_send+=conn.send(full_msg[current_send:])

def pack_msg(msg,packet_type_id:int,SenderSubClient:int=0,TargetSubClient:int=0):
    '''特定mc类型的数据包编码为字节形式'''
    encode_func=mcp.packet_encode_pool[packet_type_id]
    e=mcp.BufferEncoder()
    e.write_var_uint32(packet_type_id|(SenderSubClient<<10)|(TargetSubClient<<12))
    e=encode_func(e,msg)
    return e.bytes
    
def pack_ws_command(command:str,uuid:UUID=None):
    '''返回的uuid_bytes代表附加于这条指令的uuid，bytes，大端序'''
    if uuid is None:
        uuid=uuid1()
    # 搞不懂fb究竟想干嘛
    request_id="96045347-a6a3-4114-94c0-1bc4cc561694"
    uuid_bytes=uuid.bytes
    origin=mcp.CommandOrigin(
        Origin=mcp.CommandOriginAutomationPlayer,
        UUID=uuid_bytes,
        RequestID=request_id,
        PlayerUniqueID=0
    )
    commandRequest=mcp.CommandRequest(
        CommandLine=command,
        CommandOrigin=origin,
        Internal=False,
        UnLimited=False
    )
    return uuid_bytes,pack_msg(commandRequest,mcp.IDCommandRequest)

def fetch_thread_func(connection:socket.socket, queue:Queue,quit_queue:Queue):
    '''
        需要一个专门的线程来接收输入，
        理论上 epoll 和 asyncio 是最优选项，但是对python版本有要求
    '''
    buffed_bytes=b''
    required_bytes=0
    current_bytes=0
    try:
        while True:
            if required_bytes==0:
                recv_bytes=connection.recv(BUFFER_SIZE)
                if recv_bytes==b'':
                    print('connection closed!')
                    return
                buffed_bytes+=recv_bytes
                current_bytes=len(buffed_bytes)
                if current_bytes>=4:
                    required_bytes = struct.unpack('I',buffed_bytes[:4])[0]
            if current_bytes<required_bytes:
                recv_bytes=connection.recv(BUFFER_SIZE)
                if recv_bytes==b'':
                    print('connection closed!')
                    return
                buffed_bytes+=recv_bytes
                current_bytes=len(buffed_bytes)
            if current_bytes>=required_bytes:
                msg=buffed_bytes[4:required_bytes]
                # print('recv: ',msg)
                # queue.put(msg)
                decoded_msg=prase_msg(msg)
                if decoded_msg is not None:
                    queue.put(decoded_msg)
                buffed_bytes=buffed_bytes[required_bytes:]
                current_bytes -= required_bytes
                required_bytes = 0
    except Exception as e:
        print('Connection lost!')
        quit_queue.put(True)
        connection.close()
        raise e

def work_thread_func(connection:socket.socket, recv_queue:Queue,quit_queue:Queue):
    try:
        while True:
            command=input('cmd:')
            uuid_bytes,bytes_to_send=pack_ws_command(command)
            print(uuid_bytes)
            send_msg(connection,bytes_to_send)
            print('send complete')
    except Exception as e:
        print('Working thread terminated!')
        quit_queue.put(True)
        connection.close()
        raise e
        
if __name__=="__main__":
    # 建立和fb的链接
    connection=connect_to_fb_transfer(port=8000)
    quit_queue = Queue()
    # 建立一个后台线程去处理从fb收到的数据
    recv_queue = Queue()
    recv_thread = Thread(target=fetch_thread_func, args=(connection, recv_queue,quit_queue))
    recv_thread.daemon = True
    recv_thread.start()
 
    work_thread = Thread(target=work_thread_func, args=(connection, recv_queue,quit_queue))
    work_thread.daemon = True
    work_thread.start()   
    
    quit_queue.get(block=True)
    
