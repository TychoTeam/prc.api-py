from typing import Optional, TYPE_CHECKING, Dict
from ..player import Player
from enum import Enum

if TYPE_CHECKING:
    from prc.server import Server


class PlayerPermission(Enum):
    """Enum that represents a server player permission level."""

    @staticmethod
    def parse(permissions: str):
        mapping = {
            "Normal": PlayerPermission.NORMAL,
            "Server Moderator": PlayerPermission.MOD,
            "Server Administrator": PlayerPermission.ADMIN,
            "Server Co-Owner": PlayerPermission.CO_OWNER,
            "Server Owner": PlayerPermission.OWNER,
        }
        return mapping.get(permissions, PlayerPermission.NORMAL)

    NORMAL = 0
    MOD = 1
    ADMIN = 2
    CO_OWNER = 3
    OWNER = 4


class PlayerTeam(Enum):
    """Enum that represents a server player team."""

    @staticmethod
    def parse(team: str):
        mapping = {
            "Civilian": PlayerTeam.CIVILIAN,
            "Sheriff": PlayerTeam.SHERIFF,
            "Police": PlayerTeam.POLICE,
            "Fire": PlayerTeam.FIRE,
            "DOT": PlayerTeam.DOT,
        }
        return mapping.get(team, PlayerTeam.CIVILIAN)

    CIVILIAN = 0
    SHERIFF = 1
    POLICE = 2
    FIRE = 3
    DOT = 4


class ServerPlayer(Player):
    """Represents a full player in a server."""

    def __init__(self, server: "Server", data: Dict):
        self._server = server

        self.permission = PlayerPermission.parse(data.get("Permission"))
        self.callsign: Optional[str] = data.get("Callsign")
        self.team = PlayerTeam.parse(data.get("Team"))

        super().__init__(server._client, data=data.get("Player"))
        server._server_cache.players.set(self.id, self)

    @property
    def joined_at(self):
        return next(
            (
                entry.created_at
                for entry in self._server._server_cache.join_logs.items()
                if entry.player.id == self.id and entry.is_join
            ),
            None,
        )

    def is_staff(self):
        return self.permission != PlayerPermission.NORMAL

    def is_leo(self):
        return self.team in (PlayerTeam.SHERIFF, PlayerTeam.POLICE)


class QueuedPlayer:
    """Represents a server player in the server join queue."""

    def __init__(self, server: "Server", id: int):
        self._server = server

        self.id = int(id)
