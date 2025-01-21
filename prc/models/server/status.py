from typing import TYPE_CHECKING, Dict
from enum import Enum

if TYPE_CHECKING:
    from prc.server import Server


class ServerOwner:
    """Represents a server [co-]owner partial player."""

    def __init__(self, server: "Server", id: int):
        self._server = server

        self.id = int(id)

    @property
    def player(self):
        return self._server._get_player(id=self.id)


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

    def __init__(self, server: "Server", data: Dict):
        self.name: str = str(data.get("Name"))
        server.name = self.name
        self.owner = ServerOwner(server, id=data.get("OwnerId"))
        server.owner = self.owner
        self.co_owners = [
            ServerOwner(server, id=co_owner_id)
            for co_owner_id in data.get("CoOwnerIds")
        ]
        server.co_owners = self.co_owners
        self.player_count: int = int(data.get("CurrentPlayers"))
        server.player_count = self.player_count
        self.max_players: int = int(data.get("MaxPlayers"))
        server.max_players = self.max_players
        self.join_key: str = str(data.get("JoinKey"))
        server.join_key = self.join_key
        self.account_requirement = AccountRequirement.parse(data.get("AccVerifiedReq"))
        server.account_requirement = self.account_requirement
        self.team_balance: bool = bool(data.get("TeamBalance"))
        server.team_balance = self.team_balance
