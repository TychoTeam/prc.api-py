import re
from typing import TYPE_CHECKING, Tuple
from prc.utility import DisplayNameEnum
from .player import Player

if TYPE_CHECKING:
    from prc.server import Server
    from prc.webhook import Webhook


class WebhookPlayer(Player):
    """Represents a player referenced in a webhook message."""

    def __init__(self, server: "Server", data: Tuple[str, str]):
        self._server = server

        super().__init__(server._client, data=data)

    @property
    def player(self):
        """The full server player, if found."""
        return self._server._get_player(id=self.id)


class WebhookType(DisplayNameEnum):
    """Enum that represents a type of the webhook message."""

    COMMAND = (0, "Command Usage")
    KICK = (1, "Players Kicked")
    BAN = (2, "Players Banned")


class WebhookMessage:
    """Represents a webhook message."""

    def __init__(
        self,
        webhooks: "Webhook",
        type: WebhookType,
        version: int,
        title: str,
        description: str,
        footer: str,
    ):
        self._webhooks = webhooks

        author = re.search(
            r"^\[([^\]:]+)(?::(\d+))?]\(.+/users/(\d+)/profile\)", description
        )
        if not matched:
            raise ValueError(f"Malformed description received: {description}")

        return (str(matched.group(2) or matched.group(3)), str(matched.group(1)))
