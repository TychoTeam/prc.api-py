from typing import List, Optional, Tuple, TYPE_CHECKING, Union, overload
from prc.utility import DisplayNameEnum
from ..player import Player

if TYPE_CHECKING:
    from prc.server import Server
    from prc.api_types.v1 import v1_ServerPlayer
    from .vehicle import Vehicle


class PlayerPermission(DisplayNameEnum):
    """
    Enum that represents a server player permission level.
    """

    NORMAL = (0, "Normal")
    HELPER = (5, "Server Helper")
    MOD = (1, "Server Moderator")
    ADMIN = (2, "Server Administrator")
    CO_OWNER = (3, "Server Co-Owner")
    OWNER = (4, "Server Owner")

    __hierarchy__: List[int] = [
        p[0] for p in [NORMAL, HELPER, MOD, ADMIN, CO_OWNER, OWNER]
    ]

    def __gt__(self, other: Union[int, "PlayerPermission"]) -> bool:
        if isinstance(other, PlayerPermission):
            other = other.value
        return other in self.__hierarchy__ and (
            self.__hierarchy__.index(self.value) > self.__hierarchy__.index(other)
        )

    def __ge__(self, other: Union[int, "PlayerPermission"]) -> bool:
        return self.__gt__(other) or self.__eq__(other)

    def __lt__(self, other: Union[int, "PlayerPermission"]) -> bool:
        return not self.__gt__(other)

    def __le__(self, other: Union[int, "PlayerPermission"]) -> bool:
        return self.__lt__(other) or self.__eq__(other)


class PlayerTeam(DisplayNameEnum):
    """
    Enum that represents a server player team.
    """

    CIVILIAN = (0, "Civilian")
    SHERIFF = (1, "Sheriff")
    POLICE = (2, "Police")
    FIRE = (3, "Fire")
    DOT = (4, "DOT")
    JAIL = (5, "Jail")


class ServerPlayer(Player):
    """
    Represents a full player in a server.

    Parameters
    ----------
    server
        The server handler.
    data
        The response data.
    """

    permission: PlayerPermission
    callsign: Optional[str]
    team: PlayerTeam

    def __init__(self, server: "Server", data: "v1_ServerPlayer"):
        self._server = server

        self.permission = PlayerPermission.parse(data["Permission"])
        self.callsign = data.get("Callsign", None)
        self.team = PlayerTeam.parse(data["Team"])

        super().__init__(server._client, data=data["Player"])

        if not self.is_remote():
            server._server_cache.players.set(self.id, self)

        if self.permission == PlayerPermission.OWNER:
            server.owner = ServerOwner(server, self.id, self.permission)

    @property
    def joined_at(self):
        """
        When this player last joined the server. Server access (join/leave) logs must be fetched separately.
        """

        return next(
            (
                entry.created_at
                for entry in self._server._server_cache.access_logs.items()
                if entry.subject.id == self.id and entry.is_join()
            ),
            None,
        )

    @property
    def vehicle(self) -> Optional["Vehicle"]:
        """
        The player's currently spawned **primary** vehicle. Use `secondary_vehicle` for secondary vehicle or `vehicles` for both. Server vehicles must be fetched separately.
        """

        return next(
            (vehicle for vehicle in self.vehicles if not vehicle.is_secondary()), None
        )

    @property
    def secondary_vehicle(self) -> Optional["Vehicle"]:
        """
        The player's currently spawned **secondary** vehicle. Use `vehicle` for primary vehicle or `vehicles` for both. Server vehicles must be fetched separately.
        """

        return next(
            (vehicle for vehicle in self.vehicles if vehicle.is_secondary()), None
        )

    @property
    def vehicles(self) -> List["Vehicle"]:
        """
        The player's spawned vehicles. Each player can have up to 2 spawned vehicles (1 primary and 1 secondary). Server vehicles must be fetched separately.
        """

        return [
            v for v in self._server._server_cache.vehicles.items() if v.owner == self
        ]

    def is_staff(self, include_helpers: bool = True) -> bool:
        """
        Whether this player is a server staff member based on their permission level.

        Parameters
        ----------
        include_helpers
            Whether to check for helper permissions.
        """

        return self.permission != PlayerPermission.NORMAL and (
            include_helpers or self.permission != PlayerPermission.HELPER
        )

    def is_jailed(self) -> bool:
        """
        Whether this player is jailed.
        """

        return self.team == PlayerTeam.JAIL

    def is_leo(self) -> bool:
        """
        Whether this player is on a law enforcement team.
        """

        return self.team in (PlayerTeam.SHERIFF, PlayerTeam.POLICE)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}, id={self.id}, permission={self.permission.name}, team={self.team.name}>"


class ServerPlayerList(List[ServerPlayer]):
    def copy(self):
        return ServerPlayerList(self)

    @overload
    def find_player(self, *, id: int, name: None = ...) -> Optional[ServerPlayer]: ...

    @overload
    def find_player(self, *, id: None = ..., name: str) -> Optional[ServerPlayer]: ...

    def find_player(
        self, *, id: Optional[int] = None, name: Optional[str] = None
    ) -> Optional[ServerPlayer]:
        """
        Find a server player using their player ID or username.
        """

        if id is not None:
            return next((p for p in self if p.id == id), None)

        if name is not None:
            return next(
                (p for p in self if p.name.lower() == name.lower().strip()), None
            )

    def get_team(self, team: PlayerTeam):
        """
        Get all players in a team.
        """

        return ServerPlayerList(p for p in self if p.team == team)

    def get_staff(self):
        """
        Get all **online** server staff players.
        """

        return ServerPlayerList(p for p in self if p.is_staff())

    def get_owner(self) -> Optional[ServerPlayer]:
        """
        Get the server owner player if they are **online**.
        """

        return next((p for p in self if p.permission == PlayerPermission.OWNER), None)

    def get_co_owners(self):
        """
        Get all **online** server co-owner players.
        """

        return ServerPlayerList(
            p for p in self if p.permission == PlayerPermission.CO_OWNER
        )

    def get_admins(self):
        """
        Get all **online** server admin players.
        """

        return ServerPlayerList(
            p for p in self if p.permission == PlayerPermission.ADMIN
        )

    def get_mods(self):
        """
        Get all **online** server mod players.
        """

        return ServerPlayerList(p for p in self if p.permission == PlayerPermission.MOD)

    def get_helpers(self):
        """
        Get all **online** server helper players.
        """

        return ServerPlayerList(
            p for p in self if p.permission == PlayerPermission.HELPER
        )

    def get_normal(self):
        """
        Get all **online** normal server players (players with no staff permissions).
        """

        return ServerPlayerList(
            p for p in self if p.permission == PlayerPermission.NORMAL
        )


class QueuedPlayer:
    """
    Represents a partial player in the server join queue.

    Parameters
    ----------
    server
        The server handler.
    id
        The player ID.
    index
        The player's queue list index.
    """

    id: int
    spot: int

    def __init__(self, server: "Server", id: int, index: int):
        self._server = server

        self.id = int(id)
        self.spot = index + 1

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, QueuedPlayer) or isinstance(other, Player)
        ) and self.id == other.id

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}, spot={self.spot}>"


class QueuedPlayerList(List[QueuedPlayer]):
    def copy(self):
        return QueuedPlayerList(self)

    def find_player(self, *, id: int) -> Optional[QueuedPlayer]:
        """
        Find a queued player using their player ID.
        """

        return next((p for p in self if p.id == id), None)


class ServerOwner:
    """
    Represents a server [co-]owner partial player.

    Parameters
    ----------
    server
        The server handler.
    id
        The player ID.
    """

    id: int
    permission: PlayerPermission

    def __init__(self, server: "Server", id: int, permission: PlayerPermission):
        self._server = server

        self.id = int(id)
        self.permission = permission

        if not server.owner:
            server.owner = self

    @property
    def player(self) -> Optional["ServerPlayer"]:
        """
        The full server player, if found.
        """

        return self._server._get_player(id=self.id)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ServerOwner) or isinstance(other, Player)
        ) and self.id == other.id

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}, permission={self.permission}>"


class StaffMember(Player):
    """
    Represents a server staff member player.

    Parameters
    ----------
    server
        The server handler.
    data
        The player name and ID.
    permission
        The player permission.
    """

    permission: PlayerPermission

    def __init__(
        self, server: "Server", data: Tuple[str, str], permission: PlayerPermission
    ):
        self._server = server

        self.permission = permission

        super().__init__(server._client, data=data)

    @property
    def player(self) -> Optional["ServerPlayer"]:
        """
        The full server player, if found.
        """

        return self._server._get_player(id=self.id)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}, id={self.id}, permission={self.permission}>"
