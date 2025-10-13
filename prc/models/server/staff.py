from typing import TYPE_CHECKING
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

    def __init__(self, server: "Server", data: "v1_ServerStaffResponse"):
        self.co_owners = [
            ServerOwner(server, id=co_owner_id) for co_owner_id in data.get("CoOwners")
        ]
        server.co_owners = self.co_owners
        self.admins = [
            StaffMember(server, data=player, permission=PlayerPermission.ADMIN)
            for player in server._parse_api_map(data.get("Admins")).items()
        ]
        server.admins = self.admins
        self.mods = [
            StaffMember(server, data=player, permission=PlayerPermission.MOD)
            for player in server._parse_api_map(data.get("Mods")).items()
        ]
        server.mods = self.mods

        server.total_staff_count = self.count()

    def count(self, dedupe: bool = True) -> int:
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
