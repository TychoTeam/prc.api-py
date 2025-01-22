from typing import TYPE_CHECKING, Dict, Optional, Callable, TypeVar, Any
from datetime import datetime
from ..player import Player
from .commands import Command

if TYPE_CHECKING:
    from prc.server import Server
    from prc.utility import KeylessCache

E = TypeVar("E")


class LogEntry:
    """Base log entry."""

    def __init__(
        self,
        data: Dict,
        cache: Optional["KeylessCache[E]"] = None,
        dedupe: Optional[Callable[[E], Any]] = None,
    ):
        self.created_at = datetime.fromtimestamp(data.get("Timestamp", 0))

        if cache is not None:
            for entry in cache.items():
                if entry.created_at == self.created_at:
                    if dedupe is not None:
                        if dedupe(entry):
                            break
                    else:
                        break
            else:
                cache.add(self)


class LogPlayer(Player):
    """Represents a player referenced in a log entry."""

    def __init__(self, server: "Server", data: str):
        self._server = server

        super().__init__(server._client, data=data)

    @property
    def player(self):
        return self._server._get_player(id=self.id)


class JoinEntry(LogEntry):
    """Represents a server player join/leave log entry."""

    def __init__(self, server: "Server", data: Dict):
        self._server = server

        self.player = LogPlayer(server, data=data.get("Player"))
        self.is_join: bool = bool(data.get("Join", False))

        super().__init__(
            data,
            cache=server._server_cache.join_logs,
            dedupe=lambda e: e.player.id == self.player.id,
        )


class KillEntry(LogEntry):
    """Represents a server player kill log entry."""

    def __init__(self, server: "Server", data: Dict):
        self._server = server

        self.killed = LogPlayer(server, data=data.get("Killed"))
        self.killer = LogPlayer(server, data=data.get("Killer"))

        super().__init__(data)


class CommandEntry(LogEntry):
    """Represents a server command execution log entry."""

    def __init__(self, server: "Server", data: Dict):
        self._server = server

        self.author = LogPlayer(server, data=data.get("Player"))
        self.command = Command(server, data=data.get("Command"), author=self.author)

        super().__init__(data)


class ModCallEntry(LogEntry):
    """Represents a server mod call log entry."""

    def __init__(self, server: "Server", data: Dict):
        self._server = server

        self.caller = LogPlayer(server, data=data.get("Caller"))
        responder = data.get("Moderator")
        self.responder = LogPlayer(server, data=responder) if responder else None
        self.is_acknowledged: bool = bool(self.responder)

        super().__init__(data)
