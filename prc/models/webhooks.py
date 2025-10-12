from typing import TYPE_CHECKING, Literal, Optional, Tuple
from prc.utility import DisplayNameEnum
from .player import Player

if TYPE_CHECKING:
    from prc.client import PRC
    from prc.server import Server
    from prc.webhooks import Webhooks
    from .commands import Command


WebhookVersion = Literal[1, 2]


class WebhookPlayer(Player):
    """Represents a player referenced in a webhook message."""

    def __init__(
        self, data: Tuple[str, str], client: "PRC", server: Optional["Server"]
    ):
        self._client = client
        self._server = server

        super().__init__(client, data=data)

    @property
    def player(self):
        """The full server player, if found."""
        if self._server:
            return self._server._get_player(id=self.id)
        return None


class WebhookType(DisplayNameEnum):
    """Enum that represents webhook message type."""

    COMMAND = (0, "Command Usage")
    KICK = (1, "Players Kicked")
    BAN = (2, "Players Banned")


class WebhookMessage:
    """Represents a webhook message."""

    def __init__(
        self,
        webhooks: "Webhooks",
        type: WebhookType,
        version: WebhookVersion,
        command: "Command",
        author: WebhookPlayer,
        server: Optional["Server"] = None,
    ):
        self._webhooks = webhooks
        self._server = server

        self.type = type
        self.command = command
        self.author = author
        self.version = version

    def __repr__(self) -> str:
        return f"<{self.type.name} {self.__class__.__name__}, command={self.command}, author={self.author}, version={self.version}>"
