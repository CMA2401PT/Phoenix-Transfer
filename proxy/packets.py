from typing import List
from dataclasses import dataclass

# only a very small part of packets...
# go to fb/minecraft/protocol/packet/pool.go for full list

IDLogin=1
IDText=9 
IDSetTime=10
IDMovePlayer=19
IDClientBoundMapItemData=67
IDCommandRequest=77
IDCommandOutput=79
IDSettingsCommand=140

# Login 
@dataclass
class Login:
    ClientProtocol:int
    ConnectionRequest:bytes
    
    
# Text 
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
# IDSetTime
@dataclass 
class SetTime:
    Time:int

# MovePlayer
MoveModeTeleport=2
class MovePlayer:
    EntityRuntimeID:int
    Position:tuple
    Pitch:float
    Yaw:float
    HeadYaw:float
    Mode:int 
    OnGround:bool
    RiddenEntityRuntimeID:int 
    TeleportCause:int 
    TeleportSourceEntityType:int
    Counter:int

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
    
# CommandOutputMessage
@dataclass
class CommandOutputMessage:
    Success:bool=False
    Message:str =''
    Parameters:List[str]=None
    
#CommandRequest
@dataclass
class CommandRequest:
    CommandLine:str=''
    CommandOrigin:CommandOrigin=None
    Internal:bool=False
    UnLimited:bool=False

# CommandOutput
@dataclass
class CommandOutput:
    CommandOrigin:CommandOrigin=None
    OutputType:int=0
    SuccessCount:int=0
    OutputMessages:List[CommandOutputMessage]=None
    UnknownString:str=''

# SettingsCommand
@dataclass
class SettingsCommand:
    CommandLine:str
    SuppressOutput:bool

packet_pool={
    IDLogin:Login,
    IDText:Text,
    IDCommandRequest:CommandRequest,
    IDCommandOutput:CommandOutput,
    IDSettingsCommand:SettingsCommand
}
