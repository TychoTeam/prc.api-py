from typing import TYPE_CHECKING, Literal, Optional, Tuple
from prc.utility import DisplayNameEnum
from .player import Player

if TYPE_CHECKING:
    from prc.client import PRC
    from prc.server import Server
    from prc.webhooks import Webhooks
    from prc.models import ServerPlayer
    from .commands import Command


WebhookVersion = Literal[1, 2]


class WebhookPlayer(Player):
    """
    Represents a player referenced in a webhook message.

    Parameters
    ----------
    client
        The global/shared PRC client.
    data
        The player name and ID.
    server
        The server handler, if any.
    """

    def __init__(
        self,
        client: "PRC",
        data: Tuple[str, str],
        server: Optional["Server"] = None,
    ):
        self._client = client
        self._server = server

        super().__init__(client, data=data)

    @property
    def player(self) -> Optional["ServerPlayer"]:
        """
        The full server player, if found.
        """

        if self._server:
            return self._server._get_player(id=self.id)
        return None


class WebhookType(DisplayNameEnum):
    """
    Enum that represents webhook message type.
    """

    COMMAND = (0, "Command Usage")
    KICK = (1, "Players Kicked")
    BAN = (2, "Players Banned")


class WebhookMessage:
    """
    Represents a webhook message.

    Parameters
    ----------
    webhooks
        An initialized webhooks handler.
    type
        The type of the webhook message.
    version
        The version of the webhook message.
    command
        The command referenced in the webhook message.
    author
        The author of the webhook message.
    server
        The server handler, if any.
    """

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
