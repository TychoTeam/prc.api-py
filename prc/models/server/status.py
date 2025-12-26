from .player import PlayerPermission, ServerOwner
from prc.utility import DisplayNameEnum
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from prc.server import Server
    from prc.api_types.v1 import v1_ServerStatusResponse


class AccountRequirement(DisplayNameEnum):
    """
    Enum that represents a server account verification requirements that players must fulfill in order to join.
    """

    DISABLED = (0, "Disabled")
    EMAIL = (1, "Email")
    PHONE_OR_ID = (2, "Phone/ID")


class ServerStatus:
    """
    Represents a server status with information about the server.

    Parameters
    ----------
    server
        The server handler.
    data
        The response data.
    """

    name: str
    owner: ServerOwner
    co_owners: List[ServerOwner]
    player_count: int
    max_players: int
    join_code: str
    account_requirement: AccountRequirement
    team_balance: bool

    def __init__(self, server: "Server", data: "v1_ServerStatusResponse"):
        self.name = data["Name"]
        server.name = self.name
        self.owner = ServerOwner(
            server, id=data["OwnerId"], permission=PlayerPermission.OWNER
        )
        server.owner = self.owner
        self.co_owners = [
            ServerOwner(server, id=co_owner_id, permission=PlayerPermission.CO_OWNER)
            for co_owner_id in data["CoOwnerIds"]
        ]
        server.co_owners = self.co_owners
        self.player_count = int(data["CurrentPlayers"])
        server.player_count = self.player_count
        self.max_players = int(data["MaxPlayers"])
        server.max_players = self.max_players
        self.join_code = str(data["JoinKey"])
        server.join_code = self.join_code
        server._client._global_cache.join_codes.set(self.join_code, server._id)
        self.account_requirement = AccountRequirement.parse(data["AccVerifiedReq"])
        server.account_requirement = self.account_requirement
        self.team_balance = bool(data["TeamBalance"])
        server.team_balance = self.team_balance

    @property
    def join_link(self) -> str:
        """
        Web URL that allows users to join the game and queue automatically for the private server. Hosted by PRC. Server status must be fetched separately.

        ⚠️ *May not function properly on mobile devices.*
        """

        return "https://policeroleplay.community/join/" + self.join_code

    def is_online(self) -> bool:
        """
        Whether the server is online (i.e, has any online players). May not be always up to date; re-fetch to get latest status.
        """

        return self.player_count > 0

    def is_full(self, *, include_reserved: bool = False) -> bool:
        """
        Whether the server player count has reached the max player limit. May not be always up to date; re-fetch to get latest status.

        Parameters
        ----------
        include_reserved
            Whether to include the owner-reserved spot. By default, it is excluded (i.e, `max_players - 1`).
        """

        return self.player_count >= self.max_players - (0 if include_reserved else 1)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}, owner={self.owner.id}, join_code={self.join_code}>"
