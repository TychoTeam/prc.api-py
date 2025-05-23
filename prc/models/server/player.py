from typing import Optional, TYPE_CHECKING
from ..player import Player
from enum import Enum

if TYPE_CHECKING:
    from prc.server import Server
    from prc.api_types.v1 import ServerPlayerResponse


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

    def __init__(self, server: "Server", data: "ServerPlayerResponse"):
        self._server = server

        self.permission = PlayerPermission.parse(data.get("Permission"))
        self.callsign: Optional[str] = data.get("Callsign")
        self.team = PlayerTeam.parse(data.get("Team"))

        super().__init__(server._client, data=data.get("Player"))

        if not self.is_remote():
            server._server_cache.players.set(self.id, self)

    @property
    def joined_at(self):
        """When this player last joined the server. Server access (join/leave) logs must be fetched separately."""
        return next(
            (
                entry.created_at
                for entry in self._server._server_cache.access_logs.items()
                if entry.subject.id == self.id and entry.is_join()
            ),
            None,
        )

    @property
    def vehicle(self):
        """The player's currently spawned **primary** vehicle. Server vehicles must be fetched separately."""
        return next(
            (
                vehicle
                for vehicle in self._server._server_cache.vehicles.items()
                if vehicle.owner.name == self.name and not vehicle.is_secondary()
            ),
            None,
        )

    def is_staff(self) -> bool:
        """Whether this player is a server staff member based on their permission level."""
        return self.permission != PlayerPermission.NORMAL

    def is_leo(self) -> bool:
        """Whether this player is on a law enforcement team."""
        return self.team in (PlayerTeam.SHERIFF, PlayerTeam.POLICE)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}, id={self.id}, permission={self.permission.name}, team={self.team.name}>"


class QueuedPlayer:
    """Represents a partial player in the server join queue."""

    def __init__(self, server: "Server", id: int, index: int):
        self._server = server

        self.id = int(id)
        self.spot = index + 1

    def __eq__(self, other: object) -> bool:
        if isinstance(other, QueuedPlayer):
            return self.id == other.id
        return False

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}, spot={self.spot}>"
