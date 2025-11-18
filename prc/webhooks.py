from typing import TYPE_CHECKING, Optional, Union, overload
from .exceptions import PRCException
from .models import *
import re


if TYPE_CHECKING:
    from .server import Server
    from .client import PRC


class Webhooks:
    """
    The main class to interface with the PRC ER:LC server log webhook message parsers.

    Parameters
    ----------
    client
        The global/shared PRC client.
    """

    def __init__(self, client: "PRC"):
        self._client = client

    def get_type(
        self, *, title: str, command_name: Optional["CommandName"] = None
    ) -> WebhookType:
        """
        Determine the type of a webhook message.

        Parameters
        ----------
        title
            The webhook message embed title.
        command_name
            The used command's name.
        """

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

    def get_author(
        self, *, description: str, server: Optional["Server"] = None
    ) -> WebhookPlayer:
        """
        Get the author of a webhook message.

        Parameters
        ----------
        description
            The webhook message embed description.
        server
            The server handler, if any.
        """

        if matched := re.search(
            r"^\[([^\]:]+)(?::(\d+))?]\(.+/users/(\d+)/profile\)", description
        ):
            return WebhookPlayer(
                self._client,
                (str(matched.group(2) or matched.group(3)), str(matched.group(1))),
                server,
            )
        raise ValueError(
            f"Malformed description, could not determine author: {description}"
        )

    def get_command(
        self, *, description: str, author: Player, server: Optional["Server"] = None
    ) -> "Command":
        """
        Get the command used in a webhook message.

        Parameters
        ----------
        description
            The webhook message embed description.
        author
            The webhook message's author player.
        server
            The server handler, if any.
        """

        content: str
        version = self._get_version(description=description)
        if version == 1:
            if matched := re.search(r"\"(.+)\"$", description, flags=re.S):
                content = matched.group(1)
            else:
                raise ValueError(
                    f"Malformed description, could not determine command (v1): {description}"
                )

        elif version == 2:
            if matched := re.search(
                r"(kicked|banned|) `(.+)`$", description, flags=re.S
            ):
                keyword = matched.group(1)
                content = matched.group(2)

                if keyword == "kicked":
                    content = ":kick " + content
                if keyword == "banned":
                    content = ":ban " + content

                content = content.replace(" - Player Not In Game", "", 1)

            else:
                raise ValueError(
                    f"Malformed description, could not determine command (v2): {description}"
                )

        else:
            raise ValueError(f"Unknown webhook version: {version}")

        return Command(
            content,
            author=author,
            client=self._client,
            server=server,
            is_webhook=True,
        )

    def get_join_code(self, *, footer: str) -> str:
        """
        Get the unique server join code of a webhook message.

        Parameters
        ----------
        footer
            The webhook message embed footer.
        """

        if not footer.startswith("Private Server: "):
            raise ValueError(f"Invalid footer format: {footer}")
        return footer.split(" ")[-1]

    @overload
    def is_valid(self, *, embed: object) -> bool: ...

    @overload
    def is_valid(self, *, title: str, description: str, footer: str) -> bool: ...

    def is_valid(
        self,
        *,
        embed: Optional[object] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        footer: Optional[str] = None,
    ) -> bool:
        """
        Check whether a message is a valid webhook message.

        Parameters
        ----------
        embed
            The webhook message embed. This object must have the following attributes: "title", "description", "footer.text" (nested).
        title
            The webhook message embed title.
        description
            The webhook message embed description.
        footer
            The webhook message embed footer.
        """

        try:
            if embed:
                self.parse(embed=embed)
            else:
                assert title and description and footer
                self.parse(title=title, description=description, footer=footer)
        except Exception:
            return False

        return True

    @overload
    def parse(self, *, embed: object) -> WebhookMessage: ...

    @overload
    def parse(self, *, title: str, description: str, footer: str) -> WebhookMessage: ...

    def parse(
        self,
        *,
        embed: Optional[object] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        footer: Optional[str] = None,
    ) -> WebhookMessage:
        """
        Parse a webhook message.

        Parameters
        ----------
        embed
            The webhook message embed. This object must have the following attributes: "title", "description", "footer.text" (nested).
        title
            The webhook message embed title.
        description
            The webhook message embed description.
        footer
            The webhook message embed footer.
        """

        if hasattr(embed, "title"):
            title = getattr(embed, "title", None)
            description = getattr(embed, "description", None)
            footer_obj = getattr(embed, "footer", None)
            footer = getattr(footer_obj, "text", None) if footer_obj else None

        if not isinstance(title, str):
            raise ValueError(f"Invalid or missing title: {title}")

        if not isinstance(description, str):
            raise ValueError(f"Invalid or missing title: {description}")

        if not isinstance(footer, str):
            raise ValueError(f"Invalid or missing title: {footer}")

        server = self._get_server(footer=footer)
        version = self._get_version(description=description)
        author = self.get_author(description=description, server=server)
        command = self.get_command(
            description=description, author=author, server=server
        )
        type = self.get_type(title=title, command_name=command.name)

        return WebhookMessage(self, type, version, command, author, server)

    @overload
    def safe_parse(self, *, embed: object) -> Optional[WebhookMessage]: ...

    @overload
    def safe_parse(
        self, *, title: str, description: str, footer: str
    ) -> Optional[WebhookMessage]: ...

    def safe_parse(
        self,
        *,
        embed: Optional[object] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        footer: Optional[str] = None,
    ) -> Optional[WebhookMessage]:
        """
        Safely parse a webhook message without raising any exceptions.

        Parameters
        ----------
        embed
            The webhook message embed. This object must have the following attributes: "title", "description", "footer.text" (nested).
        title
            The webhook message embed title.
        description
            The webhook message embed description.
        footer
            The webhook message embed footer.
        """

        try:
            if embed:
                return self.parse(embed=embed)
            else:
                assert title and description and footer
                return self.parse(title=title, description=description, footer=footer)
        except Exception:
            return None

    def _get_server(self, *, footer: str) -> Optional["Server"]:
        join_code = self.get_join_code(footer=footer)
        server_id = self._client._global_cache.join_codes.get(join_code)
        if server_id:
            return self._client._global_cache.servers.get(server_id)

    def _get_version(self, *, description: str) -> WebhookVersion:
        if description[-1] == '"':
            return 1
        if description[-1] == "`":
            return 2
        raise PRCException(f"Unknown webhook message version: '{description}'")

        # 'Command Usage' - 17/01/2022 - v1 + v2

        # 'Kick/Ban Command Usage' - 17/01/2022 - v1

        # 'Player Banned' - 09/03/2023 - v2
        # aka. 'Players Banned'

        # 'Player Kicked' - 09/03/2023 - v2
        # aka. 'Players Kicked'

        # ==========
        # v1 release
        # 17/01/2022

        # v2 release
        # 09/03/2023 3:45 AM
