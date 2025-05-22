from typing import TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from prc.server import Server
    from prc.api_types.v1 import ServerStatusResponse


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
        if isinstance(other, ServerOwner):
            return self.id == other.id
        return False

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}>"


class AccountRequirement(Enum):
    """Enum that represents a server account verification requirements that players must fulfill in order to join."""

    @staticmethod
    def parse(requirement: str):
        mapping = {
            "Disabled": AccountRequirement.DISABLED,
            "Email": AccountRequirement.EMAIL,
            "Phone/ID": AccountRequirement.PHONE_OR_ID,
        }
        return mapping.get(requirement, AccountRequirement.DISABLED)

    DISABLED = 0
    EMAIL = 1
    PHONE_OR_ID = 2


class ServerStatus:
    """Represents a server status with information about the server."""

    def __init__(self, server: "Server", data: "ServerStatusResponse"):
        self.name = str(data.get("Name"))
        server.name = self.name
        self.owner = ServerOwner(server, id=data.get("OwnerId"))
        server.owner = self.owner
        self.co_owners = [
            ServerOwner(server, id=co_owner_id)
            for co_owner_id in data.get("CoOwnerIds")
        ]
        server.co_owners = self.co_owners
        self.player_count = int(data.get("CurrentPlayers"))
        server.player_count = self.player_count
        self.max_players = int(data.get("MaxPlayers"))
        server.max_players = self.max_players
        self.join_code = str(data.get("JoinKey"))
        server.join_code = self.join_code
        server._client._global_cache.join_codes.set(self.join_code, server._id)
        self.account_requirement = AccountRequirement.parse(data.get("AccVerifiedReq"))
        server.account_requirement = self.account_requirement
        self.team_balance = bool(data.get("TeamBalance"))
        server.team_balance = self.team_balance

    @property
    def join_link(self):
        """Web URL that allows users to join the game and queue automatically for the server. Hosted by PRC. ⚠️ *(May not function properly on mobile devices -- May not function at random times)*"""
        return "https://policeroleplay.community/join/" + self.join_code

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} name={self.name}, join_code={self.join_code}>"
        )
