from typing import TYPE_CHECKING, Optional
from .exceptions import PRCException
from .models import WebhookType


if TYPE_CHECKING:
    from .client import PRC
    from .models import CommandName


class Webhook:
    """The main class to interface with the PRC ER:LC server log webhook message parsers."""

    def __init__(self, client: "PRC"):
        self._client = client

    def get_type(self, title: str, command_name: Optional["CommandName"] = None):
        """Determine the type of a webhook message."""
        if title.title() == "Kick/Ban Command Usage":
            if command_name == "kick":
                return WebhookType.KICK
            if command_name == "ban":
                return WebhookType.BAN
            if not command_name:
                raise ValueError(
                    "A v1 kick/ban webhook must have a command name to determine its type."
                )
            else:
                raise ValueError(
                    f"Malformed v1 kick/ban webhook command: {command_name}"
                )
        return WebhookType.parse(title.replace("Player ", "Players "))

    def parse(self, title: str, description: str, footer: str):
        """Parse a webhook message."""

    def _get_join_code(self, footer: str):
        if not footer.startswith("Private Server: "):
            raise ValueError(f"Invalid footer format: {footer}")
        return footer.split(" ")[-1]

    def _get_server(self, join_code: str):
        server_id = self._client._global_cache.join_codes.get(join_code)
        if server_id:
            return self._client._global_cache.servers.get(server_id)

    def _get_version(self, description: str):
        if description[-1] == '"':
            return 1
        if description[-1] == "`":
            return 2
        raise PRCException("Could not identify webhook message version.")


# 2,017,584 - command logs
# 835,863 - melonly
# 163,197 - barry
# 3,016,617 - total

# types DD/MM//YYYY
# Command Usage - 17/01/2022 - v1
# Kick/Ban Command Usage - 17/01/2022 - v1
# Player Banned - 09/03/2023 - v2
# Players Banned
# Player Kicked - 09/03/2023 - v2
# Players Kicked

# v2 release https://discord.com/channels/900141799992078397/932468558682783754/1083188611257729054
# 09/03/2023 3:45 AM
