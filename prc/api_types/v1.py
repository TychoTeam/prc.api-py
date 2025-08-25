from typing import TypedDict, List, Optional, Literal, Dict, Union, TypeVar

V = TypeVar("V")

# since the API uses "maps", which are supposed to be dicts
# but when empty are actually sent as lists
_APIMap = Union[Dict[str, V], List[None]]


class v1_ServerStatusResponse(TypedDict):
    Name: str
    OwnerId: int
    CoOwnerIds: List[int]
    CurrentPlayers: int
    MaxPlayers: int
    JoinKey: str
    AccVerifiedReq: Literal["Disabled", "Email", "Phone/ID"]
    TeamBalance: bool


class v1_ServerPlayer(TypedDict):
    Player: str
    Permission: Literal[
        "Normal",
        "Server Helper",
        "Server Moderator",
        "Server Administrator",
        "Server Co-Owner",
        "Server Owner",
    ]
    Callsign: Optional[str]
    Team: Literal["Civilian", "Sheriff", "Police", "Fire", "DOT", "Jail"]


v1_ServerPlayersResponse = List[v1_ServerPlayer]


class v1_ServerJoinLog(TypedDict):
    Join: bool
    Timestamp: int
    Player: str


v1_ServerJoinLogsResponse = List[v1_ServerJoinLog]


class v1_ServerKillLog(TypedDict):
    Killed: str
    Timestamp: int
    Killer: str


v1_ServerKillLogsResponse = List[v1_ServerKillLog]


class v1_ServerCommandLog(TypedDict):
    Player: str
    Timestamp: int
    Command: str


v1_ServerCommandLogsResponse = List[v1_ServerCommandLog]


class v1_ServerModCall(TypedDict):
    Caller: str
    Moderator: Optional[str]
    Timestamp: int


v1_ServerModCallsResponse = List[v1_ServerModCall]

v1_ServerBanResponse = _APIMap[str]


class v1_ServerVehicle(TypedDict):
    Texture: Optional[str]
    Name: str
    Owner: str


v1_ServerVehiclesResponse = List[v1_ServerVehicle]

v1_ServerQueueResponse = List[int]


class v1_ServerStaffResponse(TypedDict):
    CoOwners: List[int]
    Admins: _APIMap[str]
    Mods: _APIMap[str]


class v1_ServerCommandExecutionResponse(TypedDict):
    message: str
