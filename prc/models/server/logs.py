from typing import TYPE_CHECKING, Dict, Optional, Callable, TypeVar, Any
from enum import Enum
from datetime import datetime
from ..player import Player
from ..commands import Command

if TYPE_CHECKING:
    from prc.server import Server
    from prc.utility import KeylessCache

E = TypeVar("E", bound="LogEntry")


class LogEntry:
    """Base log entry."""

    def __init__(
        self,
        data: Dict,
        cache: Optional["KeylessCache[E]"] = None,
    ):
        self.created_at = datetime.fromtimestamp(data.get("Timestamp", 0))

        if cache is not None:
            for entry in cache.items():
                if entry.created_at == self.created_at:
                    break
            else:
                cache.add(self)  # type: ignore

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
    """Represents a player referenced in a log entry."""

    def __init__(self, server: "Server", data: str):
        self._server = server

        super().__init__(server._client, data=data)

    @property
    def player(self):
        """The full server player, if found."""
        return self._server._get_player(id=self.id)


class AccessType(Enum):
    """Enum that represents a server access log entry type."""

    @staticmethod
    def parse(value: bool):
        return AccessType.JOIN if value else AccessType.LEAVE

    JOIN = 0
    LEAVE = 1


class AccessEntry(LogEntry):
    """Represents a server access (join/leave) log entry."""

    def __init__(self, server: "Server", data: Dict):
        self._server = server

        self.type = AccessType.parse(bool(data.get("Join", False)))
        self.subject = LogPlayer(server, data=data.get("Player"))  # type: ignore

        super().__init__(data, cache=server._server_cache.access_logs)

    def is_join(self) -> bool:
        return self.type == AccessType.JOIN

    def is_leave(self) -> bool:
        return self.type == AccessType.LEAVE

    def __repr__(self) -> str:
        return f"<{self.type.name} {self.__class__.__name__}, subject={self.subject.name, self.subject.id}>"


class KillEntry(LogEntry):
    """Represents a server player kill log entry."""

    def __init__(self, server: "Server", data: Dict):
        self._server = server

        self.killed = LogPlayer(server, data=data.get("Killed"))  # type: ignore
        self.killer = LogPlayer(server, data=data.get("Killer"))  # type: ignore

        super().__init__(data)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} killed={self.killed.name, self.killed.id}>"


class CommandEntry(LogEntry):
    """Represents a server command execution log entry."""

    def __init__(self, server: "Server", data: Dict):
        self._server = server

        self.author = LogPlayer(server, data=data.get("Player"))  # type: ignore
        self.command = Command(data=data.get("Command"), author=self.author, server=server)  # type: ignore

        super().__init__(data)

    def __repr__(self) -> str:
        return f"<:{self.command.name} {self.__class__.__name__} author={self.author.name, self.author.id}>"


class ModCallEntry(LogEntry):
    """Represents a server mod call log entry."""

    def __init__(self, server: "Server", data: Dict):
        self._server = server

        self.caller = LogPlayer(server, data=data.get("Caller"))  # type: ignore
        responder = data.get("Moderator")
        self.responder = LogPlayer(server, data=responder) if responder else None

        super().__init__(data)

    def is_acknowledged(self) -> bool:
        """Whether this mod call has been responded to."""
        return bool(self.responder)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} caller={self.caller.name, self.caller.id}>"
