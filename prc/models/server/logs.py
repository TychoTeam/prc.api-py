from typing import TYPE_CHECKING, Optional, Union
from enum import Enum
from datetime import datetime
from ..player import Player
from ..commands import Command

if TYPE_CHECKING:
    from prc.server import Server
    from prc.utility import KeylessCache
    from prc.api_types.v1 import (
        v1_ServerJoinLog,
        v1_ServerKillLog,
        v1_ServerCommandLog,
        v1_ServerModCall,
    )
    from .player import ServerPlayer


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

    def __init__(
        self,
        data: Union[
            "v1_ServerJoinLog",
            "v1_ServerKillLog",
            "v1_ServerCommandLog",
            "v1_ServerModCall",
        ],
        cache: Optional["KeylessCache"] = None,
    ):
        self.created_at = datetime.fromtimestamp(data.get("Timestamp", 0))

        if cache is not None:
            for entry in cache.items():
                if entry.created_at == self.created_at:
                    break
            else:
                cache.add(self)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, LogEntry):
            return self.created_at == other.created_at
        return False

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __gt__(self, other: "LogEntry"):
        return self.created_at > other.created_at

    def __lt__(self, other: "LogEntry"):
        return self.created_at < other.created_at


class LogPlayer(Player):
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

        super().__init__(server._client, data=data)

    @property
    def player(self) -> Optional["ServerPlayer"]:
        """
        The full server player, if found.
        """

        return self._server._get_player(id=self.id)


class AccessType(Enum):
    """
    Enum that represents a server access log entry type.
    """

    @staticmethod
    def parse(value: bool):
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

    def __init__(self, server: "Server", data: "v1_ServerJoinLog"):
        self._server = server

        self.type = AccessType.parse(bool(data.get("Join", False)))
        self.subject = LogPlayer(server, data=data.get("Player"))

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

    def __init__(self, server: "Server", data: "v1_ServerKillLog"):
        self._server = server

        self.killed = LogPlayer(server, data=data.get("Killed"))
        self.killer = LogPlayer(server, data=data.get("Killer"))

        super().__init__(data)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} killed={self.killed.name, self.killed.id}>"


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

    def __init__(self, server: "Server", data: "v1_ServerCommandLog"):
        self._server = server

        self.author = LogPlayer(server, data=data.get("Player"))
        self.command = Command(
            data=data.get("Command"), author=self.author, server=server
        )

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

    def __init__(self, server: "Server", data: "v1_ServerModCall"):
        self._server = server

        self.caller = LogPlayer(server, data=data.get("Caller"))
        responder = data.get("Moderator")
        self.responder = LogPlayer(server, data=responder) if responder else None

        super().__init__(data)

    def is_acknowledged(self) -> bool:
        """
        Whether this mod call has been responded to.
        """

        return bool(self.responder)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} caller={self.caller.name, self.caller.id}>"
