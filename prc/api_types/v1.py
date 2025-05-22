from typing import TypedDict, List, Optional, Literal, Dict


class ServerStatusResponse(TypedDict):
    Name: str
    OwnerId: int
    CoOwnerIds: List[int]
    CurrentPlayers: int
    MaxPlayers: int
    JoinKey: str
    AccVerifiedReq: Literal["Disabled", "Email", "Phone/ID"]
    TeamBalance: bool


class ServerPlayerResponse(TypedDict):
    Player: str
    Permission: Literal[
        "Normal",
        "Server Moderator",
        "Server Administrator",
        "Server Co-Owner",
        "Server Owner",
    ]
    Callsign: Optional[str]
    Team: Literal["Civilian", "Sheriff", "Police", "Fire", "DOT"]


class ServerJoinLogResponse(TypedDict):
    Join: bool
    Timestamp: int
    Player: str


class ServerKillLogResponse(TypedDict):
    Killed: str
    Timestamp: int
    Killer: str


class ServerCommandLogResponse(TypedDict):
    Player: str
    Timestamp: int
    Command: str


class ServerModCallResponse(TypedDict):
    Caller: str
    Moderator: Optional[str]
    Timestamp: int


ServerBanResponse = Dict[str, str]


class ServerVehicleResponse(TypedDict):
    Texture: Optional[str]
    Name: str
    Owner: str
