from typing import TYPE_CHECKING, List, Optional, Union, overload
from .player import ServerOwner, StaffMember, PlayerPermission

if TYPE_CHECKING:
    from prc.server import Server
    from prc.api_types.v2 import v2_ServerStaff


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

    owner: ServerOwner
    co_owners: List[ServerOwner]
    admins: List[StaffMember]
    mods: List[StaffMember]
    helpers: List[StaffMember]

    def __init__(self, server: "Server", data: "v2_ServerStaff"):
        self._server = server

        assert server.owner
        self.owner = server.owner

        self.co_owners = server.co_owners

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

        self.helpers = [
            StaffMember(server, data=player, permission=PlayerPermission.HELPER)
            for player in server._parse_api_map(data["Helpers"]).items()
        ]
        server.mods = self.mods

        server.total_staff_count = self.count()

    @property
    def owners(self):
        """
        Server owner and all co-owners.
        """

        assert self._server.owner
        return self._server.co_owners + [self._server.owner]

    @property
    def members(self):
        """
        All server staff members, excluding server owners.
        """

        return self.admins + self.mods + self.helpers

    @property
    def all(self):
        """
        All server staff, including server owner. Some players may have multiple permissions set, hence may be present multiple times.
        """

        assert self._server.owner
        return self.owners + self.members

    @property
    def unique(self):
        """
        All server staff, including server owner. Unlike `.all`, this property shows only unique players based on their highest permission, hence each player is guaranteed to be present only once.

        Since a player can have multiple permissions, the unique player permission will be selected based on the following order, if found:

        Owner -> Co-Owner -> Admins -> Mods -> Helpers
        """

        used = set()
        unique: List[Union[ServerOwner, StaffMember]] = []
        for p in self.all:
            if p.id not in used:
                used.add(p.id)
                unique.append(p)

        return unique

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
        Find a staff member using their player ID or username. [Co-]owners cannot be found using their usernames.

        Since a player can have multiple permissions, results will be in the following order, if found:

        Owner -> Co-Owner -> Admins -> Mods -> Helpers
        """

        if id is not None:
            return next((p for p in self.owners if p.id == id), None) or next(
                (s for s in self.members if s.id == id), None
            )

        if name is not None:
            return next(
                (s for s in self.members if s.name.lower() == name.lower().strip()),
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

    @overload
    def find_helper(self, *, id: int, name: None = ...) -> Optional[StaffMember]: ...

    @overload
    def find_helper(self, *, id: None = ..., name: str) -> Optional[StaffMember]: ...

    def find_helper(
        self, *, id: Optional[int] = None, name: Optional[str] = None
    ) -> Optional[StaffMember]:
        """
        Find a helper using their player ID or username. A player may have other permissions set. Use `find_player` to get their highest set permission.
        """

        if id is not None:
            return next((s for s in self.helpers if s.id == id), None)

        if name is not None:
            return next(
                (s for s in self.helpers if s.name.lower() == name.lower().strip()),
                None,
            )

    def count(self, *, exclude_owner: bool = False, dedupe: bool = True) -> int:
        """
        Total number of server staff.

        Parameters
        ----------
        exclude_owner
            Whether to exclude the server owner (`-1`).
        dedupe
            Whether to exclude duplicates (players with multiple permissions set). If true (default), every player will be counted **once**.
        """

        count = len({s.id for s in self.all}) if dedupe else len(self.all)
        if exclude_owner:
            count -= 1

        return count

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} count={self.count()}>"
