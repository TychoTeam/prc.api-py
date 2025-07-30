from typing import TYPE_CHECKING
from .player import ServerOwner, StaffMember, PlayerPermission

if TYPE_CHECKING:
    from prc.server import Server
    from prc.api_types.v1 import ServerStaffResponse


class ServerStaff:
    """Represents a server staff list for players with elevated permissions."""

    def __init__(self, server: "Server", data: "ServerStaffResponse"):
        self.co_owners = [
            ServerOwner(server, id=co_owner_id) for co_owner_id in data.get("CoOwners")
        ]
        server.co_owners = self.co_owners
        self.admins = [
            StaffMember(server, data=player, permission=PlayerPermission.ADMIN)
            for player in (data.get("Admins") or {}).items()
        ]
        server.admins = self.admins
        self.mods = [
            StaffMember(server, data=player, permission=PlayerPermission.MOD)
            for player in (data.get("Mods") or {}).items()
        ]
        server.mods = self.mods

    def count(self, dedupe: bool = True):
        """Total number of **unique** server staff excluding server owner. Set `dedupe=False` to include duplicates (players with multiple permissions set)."""
        all_staff = self.co_owners + self.admins + self.mods
        return len({s.id for s in all_staff}) if dedupe else len(all_staff)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} count={self.count()}>"
