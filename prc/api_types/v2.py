from typing import TypedDict, List, Optional, Literal, Dict, Union, TypeVar

V = TypeVar("V")

# since the API STILL uses "maps", which are supposed to be dicts
# but when empty are actually sent as lists
_APIMap = Union[Dict[str, V], List[None]]


class v2_ServerInformation(TypedDict):
    Name: str
    OwnerId: int
    CoOwnerIds: List[int]
    CurrentPlayers: int
    MaxPlayers: int
    JoinKey: str
    AccVerifiedReq: Literal["Disabled", "Email", "Phone/ID"]
    TeamBalance: bool


class v2_ServerPlayerLocation(TypedDict):
    LocationX: float
    LocationZ: float
    PostalCode: str
    StreetName: str
    BuildingNumber: str


class v2_ServerPlayer(TypedDict):
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
    Location: v2_ServerPlayerLocation


class v2_ServerPlayersResponse(v2_ServerInformation):
    Players: List[v2_ServerPlayer]


class v2_ServerStaff(TypedDict):
    Admins: _APIMap[str]
    Mods: _APIMap[str]
    Helpers: _APIMap[str]


class v2_ServerStaffResponse(v2_ServerInformation):
    Staff: v2_ServerStaff


class v2_ServerJoinLog(TypedDict):
    Join: bool
    Timestamp: int
    Player: str


class v2_ServerJoinLogsResponse(v2_ServerInformation):
    JoinLogs: List[v2_ServerJoinLog]


class v2_ServerQueueResponse(v2_ServerInformation):
    Queue: List[int]


class v2_ServerKillLog(TypedDict):
    Killed: str
    Timestamp: int
    Killer: str


class v2_ServerKillLogsResponse(v2_ServerInformation):
    KillLogs: List[v2_ServerKillLog]


class v2_ServerCommandLog(TypedDict):
    Player: str
    Timestamp: int
    Command: str


class v2_ServerCommandLogsResponse(TypedDict):
    CommandLogs: List[v2_ServerCommandLog]


class v2_ServerModCall(TypedDict):
    Caller: str
    Moderator: Optional[str]
    Timestamp: int


class v2_ServerModCallsResponse(v2_ServerInformation):
    ModCalls: List[v2_ServerModCall]


class v2_ServerVehicle(TypedDict):
    Name: str
    Owner: str
    Texture: Optional[str]
    ColorHex: str
    ColorName: str


class v2_ServerVehiclesResponse(v2_ServerInformation):
    Vehicles: List[v2_ServerVehicle]


class v2_FullServerInformation(
    v2_ServerPlayersResponse,
    v2_ServerStaffResponse,
    v2_ServerJoinLogsResponse,
    v2_ServerQueueResponse,
    v2_ServerKillLogsResponse,
    v2_ServerCommandLogsResponse,
    v2_ServerModCallsResponse,
    v2_ServerVehiclesResponse,
):
    pass
