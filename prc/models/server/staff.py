from typing import TYPE_CHECKING, List, Optional, Union, overload
from .player import ServerOwner, StaffMember, PlayerPermission

if TYPE_CHECKING:
    from prc.server import Server
    from prc.api_types.v1 import v1_ServerStaffResponse


class ServerStaff:
    """
    Represents a server staff list for players with elevated permissions.

    Parameters
    ----------
    server
        The server handler.
    data
        The response data.
    """

    co_owners: List[ServerOwner]
    admins: List[StaffMember]
    mods: List[StaffMember]

    def __init__(self, server: "Server", data: "v1_ServerStaffResponse"):
        self._server = server

        self.co_owners = [
            ServerOwner(server, id=co_owner_id, permission=PlayerPermission.CO_OWNER)
            for co_owner_id in data["CoOwners"]
        ]
        server.co_owners = self.co_owners
        self.admins = [
            StaffMember(server, data=player, permission=PlayerPermission.ADMIN)
            for player in server._parse_api_map(data["Admins"]).items()
        ]
        server.admins = self.admins
        self.mods = [
            StaffMember(server, data=player, permission=PlayerPermission.MOD)
            for player in server._parse_api_map(data["Mods"]).items()
        ]
        server.mods = self.mods

        server.total_staff_count = self.count()

    @property
    def all(self):
        """
        All server staff, including server owner (if cached). Some players may have multiple permissions set, hence may be present multiple times.
        """

        return self.co_owners + self.admins + self.mods + [self._server.owner]

    @overload
    def find_player(
        self, *, id: int, name: None = ...
    ) -> Optional[Union[ServerOwner, StaffMember]]: ...

    @overload
    def find_player(self, *, id: None = ..., name: str) -> Optional[StaffMember]: ...

    def find_player(
        self, *, id: Optional[int] = None, name: Optional[str] = None
    ) -> Optional[Union[ServerOwner, StaffMember]]:
        """
        Find a staff member using their player ID or username. Co-owners cannot be found using their usernames.

        Since a player can have multiple permissions, results will be in the following order, if found:

        Co-Owner -> Admins -> Mods
        """

        if id is not None:
            return next((p for p in self.co_owners if p.id == id), None) or next(
                (s for s in (self.admins + self.mods) if s.id == id), None
            )

        if name is not None:
            return next(
                (
                    s
                    for s in (self.admins + self.mods)
                    if s.name.lower() == name.lower().strip()
                ),
                None,
            )

    def find_co_owner(self, *, id: int) -> Optional[ServerOwner]:
        """
        Find a co-owner using their player ID. A player may have other permissions set. Use `find_player` to get their highest set permission.
        """

        return next((s for s in self.co_owners if s.id == id), None)

    @overload
    def find_admin(self, *, id: int, name: None = ...) -> Optional[StaffMember]: ...

    @overload
    def find_admin(self, *, id: None = ..., name: str) -> Optional[StaffMember]: ...

    def find_admin(
        self, *, id: Optional[int] = None, name: Optional[str] = None
    ) -> Optional[StaffMember]:
        """
        Find an admin using their player ID or username. A player may have other permissions set. Use `find_player` to get their highest set permission.
        """

        if id is not None:
            return next((s for s in self.admins if s.id == id), None)

        if name is not None:
            return next(
                (s for s in self.admins if s.name.lower() == name.lower().strip()), None
            )

    @overload
    def find_mod(self, *, id: int, name: None = ...) -> Optional[StaffMember]: ...

    @overload
    def find_mod(self, *, id: None = ..., name: str) -> Optional[StaffMember]: ...

    def find_mod(
        self, *, id: Optional[int] = None, name: Optional[str] = None
    ) -> Optional[StaffMember]:
        """
        Find a mod using their player ID or username. A player may have other permissions set. Use `find_player` to get their highest set permission.
        """

        if id is not None:
            return next((s for s in self.mods if s.id == id), None)

        if name is not None:
            return next(
                (s for s in self.mods if s.name.lower() == name.lower().strip()), None
            )

    def count(self, *, dedupe: bool = True) -> int:
        """
        Total number of server staff (excluding server owner).

        Parameters
        ----------
        dedupe
            Whether to exclude duplicates (players with multiple permissions set).
        """

        all_staff = self.co_owners + self.admins + self.mods
        return len({s.id for s in all_staff}) if dedupe else len(all_staff)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} count={self.count()}>"
