from .packets import *
from .buffer_io import BufferDecoder,BufferEncoder
# only a very small part of packets...
# go to fb/minecraft/protocol/packet/pool.go for full list

# Login 
def decode_login(d:BufferDecoder):
    return Login(d.read_var_uint32(),d.read_tail())

# Text 
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

def encode_text(e:BufferEncoder,i:Text):
    e.write_byte(i.TextType)
    e.write_boolen(i.NeedsTranslation)
    if i.TextType in [TextTypeChat, TextTypeWhisper, TextTypeAnnouncement]:
        e.write_str(i.SourceName)
        e.write_str(i.Message)
    elif i.TextType in [TextTypeRaw, TextTypeTip, TextTypeSystem, TextTypeObject, TextTypeObjectWhisper]:
        e.write_str(i.Message)
    elif i.TextType in [TextTypeTranslation, TextTypePopup, TextTypeJukeboxPopup]:
        e.write_str(i.Message)
        e.write_var_uint32(len(i.Parameters))
        for p in i.Parameters:
            e.write_str(p)
    e.write_str(i.XUID)
    e.write_str(i.PlatformChatID)
    if i.TextType == TextTypeChat:
        e.write_byte(2)
        e.write_str('PlayerId')
        e.write_str('-12345678')
    return e
        
# IDSetTime
def decode_set_time(d:BufferDecoder):
    # well 这里好像有问题
    o=SetTime(d.read_var_int32())
    return o
# MovePlayer
def decode_move_player(d:BufferDecoder):
    o=MovePlayer()
    o.EntityRuntimeID=d.read_var_uint64()
    o.Position=d.read_vec3()
    o.Pitch=d.read_float32()
    o.Yaw=d.read_float32()
    o.HeadYaw=d.read_float32()
    o.Mode=d.read_byte()
    o.OnGround=d.read_byte()
    o.RiddenEntityRuntimeID=d.read_var_uint64()
    if o.Mode==MoveModeTeleport:
        o.TeleportCause=d.read_int32()
        o.TeleportSourceEntityType=d.read_int32()
    o.Counter=d.read_var_uint64()
    return o
    
# CommandOrigin
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
def decode_command_message(d:BufferDecoder):
    o=CommandOutputMessage()
    o.Success=d.read_boolen()
    o.Message=d.read_str()
    count=d.read_var_uint32()
    o.Parameters=[d.read_str() for _ in range(count)]
    return o

# CommandOutput
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

# CommandRequest
def encode_command_request(e:BufferEncoder,i:CommandRequest):
    e.write_str(i.CommandLine)
    encode_command_origin_data(e,i.CommandOrigin)
    e.write_boolen(i.Internal)
    e.write_boolen(i.UnLimited)
    return e

# SettingsCommand
def encode_settings_command(e:BufferEncoder,i:SettingsCommand):
    e.write_str(i.CommandLine)
    e.write_boolen(i.SuppressOutput)
    return e

packet_encode_pool={
    IDCommandRequest:encode_command_request,
    CommandRequest:(IDCommandRequest,encode_command_request),
    IDSettingsCommand:encode_settings_command,
    SettingsCommand:(IDSettingsCommand,encode_settings_command),
    IDText:encode_text,
    Text:(IDText,encode_text)
}

packet_decode_pool={
    IDLogin:decode_login,
    IDText:decode_text,
    IDCommandOutput:decode_command_output, 
    IDMovePlayer:decode_move_player,   
    IDSetTime:decode_set_time,
}

def decode(packet:bytes):
    '''将字节形式的收到的数据包解析为特定mc类型'''
    d=BufferDecoder(packet)
    value=d.read_var_uint32()
    packet_id = value & 0x3FF
    sender_subclient=(value >> 10) & 0x3
    target_subclient=(value >> 12) & 0x3
    decode_func=packet_decode_pool.get(packet_id)
    if decode_func is None:
        # print(f'decode func not implemented: packet type id: {packet_id}')
        # print(f'forward: fb -> packet(ID={packet_id}) -> drop')
        return packet_id,None
    else:
        return packet_id,(decode_func(d),sender_subclient,target_subclient)

def encode(packet,SenderSubClient:int=0,TargetSubClient:int=0):
    '''特定mc类型的数据包编码为字节形式'''
    type_id,encode_func=packet_encode_pool[type(packet)]
    e=BufferEncoder()
    e.write_var_uint32(type_id|(SenderSubClient<<10)|(TargetSubClient<<12))
    e=encode_func(e,packet)
    return e.bytes