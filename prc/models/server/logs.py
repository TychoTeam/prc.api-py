from typing import TYPE_CHECKING, List, Optional, Tuple, Union
from enum import Enum
from datetime import datetime

from .player import PartialServerPlayer, PlayerTeam
from ..commands import Command
from ..player import Player

if TYPE_CHECKING:
    from prc.server import Server
    from prc.utility import KeylessCache
    from prc.api_types.v2 import (
        v2_ServerJoinLog,
        v2_ServerKillLog,
        v2_ServerCommandLog,
        v2_ServerModCall,
        v2_ServerEmergencyCall,
    )


class LogEntry:
    """
    Base log entry.

    Parameters
    ----------
    data
        The response data.
    cache
        The corresponding initialized cache, if any.
    """

    created_at: datetime

    def __init__(
        self,
        data: Union[
            "v2_ServerJoinLog",
            "v2_ServerKillLog",
            "v2_ServerCommandLog",
            "v2_ServerModCall",
            "v2_ServerEmergencyCall",
        ],
        cache: Optional["KeylessCache"] = None,
    ):
        time = data.get("Timestamp", data.get("StartedAt", None))
        if not time:
            raise ValueError(
                "Log entry unexpectedly has neither a timestamp nor a start time"
            )

        self.created_at = datetime.fromtimestamp(time)

        if cache is not None:
            for entry in cache.items():
                if entry.created_at == self.created_at:
                    break
            else:
                cache.add(self)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, LogEntry) and self.created_at == other.created_at

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __gt__(self, other: "LogEntry") -> bool:
        return isinstance(other, LogEntry) and self.created_at > other.created_at

    def __ge__(self, other: "LogEntry") -> bool:
        return self.__gt__(other) or self.__eq__(other)

    def __lt__(self, other: "LogEntry") -> bool:
        return not self.__gt__(other)

    def __le__(self, other: "LogEntry") -> bool:
        return self.__lt__(other) or self.__eq__(other)


class LogPlayer(Player, PartialServerPlayer):
    """
    Represents a player referenced in a log entry.

    Parameters
    ----------
    server
        The server handler.
    data
        The player name and ID (`PlayerName:123`).
    """

    def __init__(self, server: "Server", data: str):
        self._server = server

        super().__init__(client=server._client, data=data)
        self._value = self.id


class CallPlayer(PartialServerPlayer):
    """
    Represents a server partial player referenced in a call entry.

    Parameters
    ----------
    server
        The server handler.
    id
        The player ID.
    """

    id: int

    def __init__(self, server: "Server", id: int):
        self._server = server

        self.id = int(id)

        super().__init__(server, value=self.id)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}>"


class CallPlayerList(List[CallPlayer]):
    def copy(self):
        return CallPlayerList(self)

    def find_player(self, *, id: int) -> Optional[CallPlayer]:
        """
        Find a call player using their player ID.
        """

        return next((p for p in self if p.id == id), None)

    def has_player(self, *, id: int) -> bool:
        """
        Determine whether a player exists in this call player list using their player ID.
        """

        return bool(self.find_player(id=id))


class CallLocation:
    """
    Represents a call's location in a server.

    Parameters
    ----------
    data
        The call data.
    """

    x: float
    z: float
    descriptor: Optional[str]

    def __init__(self, data: "v2_ServerEmergencyCall"):
        self.x = float(data["Position"][0])
        self.z = float(data["Position"][1])
        descriptor = data.get("PositionDescriptor", None)
        self.descriptor = str(descriptor) if descriptor else None

    @property
    def coordinates(self) -> Tuple[float, float]:
        """
        A tuple representing location coordinates (x, z) on an official [PRC API map](https://apidocs.policeroleplay.community/for-developers/v2-api-reference/er-lc-location-information).
        """

        return (self.x, self.z)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CallLocation) and (
            self.coordinates == other.coordinates
        )

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} coordinates={self.coordinates}, descriptor={self.descriptor}>"


class AccessType(Enum):
    """
    Enum that represents a server access log entry type.
    """

    @staticmethod
    def parse(value: bool) -> "AccessType":
        return AccessType.JOIN if value else AccessType.LEAVE

    JOIN = 0
    LEAVE = 1


class AccessEntry(LogEntry):
    """
    Represents a server access (join/leave) log entry.

    Parameters
    ----------
    server
        The server handler.
    data
        The response data.
    """

    type: AccessType
    subject: LogPlayer

    def __init__(self, server: "Server", data: "v2_ServerJoinLog"):
        self._server = server

        self.type = AccessType.parse(bool(data["Join"]))
        self.subject = LogPlayer(server, data=data["Player"])

        super().__init__(data, cache=server._server_cache.access_logs)

    def is_join(self) -> bool:
        """
        Whether the log is a player join log.
        """

        return self.type == AccessType.JOIN

    def is_leave(self) -> bool:
        """
        Whether the log is a player leave log.
        """

        return self.type == AccessType.LEAVE

    def __repr__(self) -> str:
        return f"<{self.type.name} {self.__class__.__name__}, subject={self.subject.name, self.subject.id}>"


class KillEntry(LogEntry):
    """
    Represents a server player kill log entry.

    Parameters
    ----------
    server
        The server handler.
    data
        The response data.
    """

    killer: LogPlayer
    killed: LogPlayer

    def __init__(self, server: "Server", data: "v2_ServerKillLog"):
        self._server = server

        self.killer = LogPlayer(server, data=data["Killer"])
        self.killed = LogPlayer(server, data=data["Killed"])

        super().__init__(data)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} killer={self.killer.name, self.killer.id} killed={self.killed.name, self.killed.id}>"


class CommandEntry(LogEntry):
    """
    Represents a server command execution log entry.

    Parameters
    ----------
    server
        The server handler.
    data
        The response data.
    """

    author: LogPlayer
    command: Command

    def __init__(self, server: "Server", data: "v2_ServerCommandLog"):
        self._server = server

        self.author = LogPlayer(server, data=data["Player"])
        self.command = Command(data=data["Command"], author=self.author, server=server)

        super().__init__(data)

    def __repr__(self) -> str:
        return f"<:{self.command.name} {self.__class__.__name__} author={self.author.name, self.author.id}>"


class ModCallEntry(LogEntry):
    """
    Represents a server mod call log entry.

    Parameters
    ----------
    server
        The server handler.
    data
        The response data.
    """

    caller: LogPlayer
    responder: Optional[LogPlayer]

    def __init__(self, server: "Server", data: "v2_ServerModCall"):
        self._server = server

        self.caller = LogPlayer(server, data=data["Caller"])
        responder = data.get("Moderator", None)
        self.responder = LogPlayer(server, data=responder) if responder else None

        super().__init__(data)

    def is_acknowledged(self) -> bool:
        """
        Whether this mod call has been responded to.
        """

        return bool(self.responder)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} caller={self.caller.name, self.caller.id} acknowledged={self.is_acknowledged()}>"


class EmergencyCallEntry(LogEntry):
    """
    Represents a server emergency call log entry.

    Parameters
    ----------
    server
        The server handler.
    data
        The response data.
    """

    team: PlayerTeam
    caller: Optional[CallPlayer]
    responders: List[CallPlayer]
    location: CallLocation
    call_number: int
    description: Optional[str]

    def __init__(self, server: "Server", data: "v2_ServerEmergencyCall"):
        self._server = server

        self.team = PlayerTeam.parse(data["Team"])
        caller = data.get("Caller", None)
        self.caller = CallPlayer(server, id=int(caller)) if caller else None
        self.responders = CallPlayerList(
            CallPlayer(server, id=int(id)) for id in data["Players"]
        )
        self.location = CallLocation(data)
        self.call_number = int(self.call_number)
        description = data.get("Description", None)
        self.description = str(description) if description else None

        super().__init__(data)

    def is_911(self) -> bool:
        """
        Whether this emergency call is a player 911 call.
        """

        return bool(self.caller)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} call_number={self.call_number}, team={self.team}, caller={self.caller.id if self.caller else None}, description={self.description}, responders={len(self.responders)}>"
