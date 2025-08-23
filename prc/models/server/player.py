from typing import Optional, Tuple, TYPE_CHECKING
from prc.utility import DisplayNameEnum
from ..player import Player

if TYPE_CHECKING:
    from prc.server import Server
    from prc.api_types.v1 import v1_ServerPlayer


class PlayerPermission(DisplayNameEnum):
    """Enum that represents a server player permission level."""

    NORMAL = (0, "Normal")
    MOD = (1, "Server Moderator")
    ADMIN = (2, "Server Administrator")
    CO_OWNER = (3, "Server Co-Owner")
    OWNER = (4, "Server Owner")


class PlayerTeam(DisplayNameEnum):
    """Enum that represents a server player team."""

    CIVILIAN = (0, "Civilian")
    SHERIFF = (1, "Sheriff")
    POLICE = (2, "Police")
    FIRE = (3, "Fire")
    DOT = (4, "DOT")
    JAIL = (5, "Jail")


class ServerPlayer(Player):
    """Represents a full player in a server."""

    def __init__(self, server: "Server", data: "v1_ServerPlayer"):
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
        if isinstance(other, QueuedPlayer) or isinstance(other, Player):
            return self.id == other.id
        return False

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}, spot={self.spot}>"


class ServerOwner:
    """Represents a server [co-]owner partial player."""

    def __init__(self, server: "Server", id: int):
        self._server = server

        self.id = int(id)

    @property
    def player(self):
        """The full server player, if found."""
        return self._server._get_player(id=self.id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ServerOwner) or isinstance(other, Player):
            return self.id == other.id
        return False

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}>"


class StaffMember(Player):
    """Represents a server staff member player."""

    def __init__(
        self, server: "Server", data: Tuple[str, str], permission: PlayerPermission
    ):
        self._server = server

        self.permission = permission

        super().__init__(server._client, data=data)

    @property
    def player(self):
        """The full server player, if found."""
        return self._server._get_player(id=self.id)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}, id={self.id}>, permission={self.permission}"
