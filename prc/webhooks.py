from typing import TYPE_CHECKING, Optional, overload
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

        if title == "Kick/Ban Command Usage":
            if command_name == "kick":
                return WebhookType.KICK
            if command_name == "ban":
                return WebhookType.BAN

            if not command_name:
                raise ValueError(
                    "A v1 kick/ban webhook must have a command name to determine its type."
                )
            raise ValueError(f"Malformed v1 kick/ban webhook command: '{command_name}'")

        return WebhookType.parse(title.replace("Player ", "Players "))

    _author_expression = re.compile(
        r"^\[([^\]:]+)(?::(\d+))?]\(\S+\/users\/(\d+)/\S+\)"
    )

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

        if matched := self._author_expression.search(description):
            return WebhookPlayer(
                self._client,
                (str(matched.group(2) or matched.group(3)), str(matched.group(1))),
                server,
            )
        raise ValueError(
            f"Malformed description, could not determine author: '{description}'"
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
            start = description.find('"')
            end = description.rfind('"')

            if start == -1 or end <= start:
                raise ValueError(
                    f"Malformed description, could not determine command (v1): '{description}'"
                )

            content = description[start + 1 : end]

        elif version == 2:
            end = description.rfind("`")
            start = description.rfind("`", 0, end)

            if start == -1 or end <= start:
                raise ValueError(
                    f"Malformed description, could not determine command (v2): '{description}'"
                )

            content = description[start + 1 : end]
            prefix = description[:start].rstrip()

            if prefix.endswith("kicked"):
                content = ":kick " + content
            elif prefix.endswith("banned"):
                content = ":ban " + content

            content = content.replace(" - Player Not In Game", "", 1)

        else:
            raise ValueError(f"Unknown webhook version: '{version}'")

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

        prefix = "Private Server: "

        if not footer.startswith(prefix):
            raise ValueError(f"Invalid footer format: '{footer}'")

        join_code = footer[len(prefix) :]

        if not join_code or " " in join_code:
            raise ValueError(f"Invalid footer format: '{footer}'")

        return join_code

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
            if embed is not None:
                self.parse(embed=embed)
                return True

            if title is not None and description is not None and footer is not None:
                self.parse(
                    title=title,
                    description=description,
                    footer=footer,
                )
                return True

        except (ValueError, PRCException):
            return False

        return False

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

        if any(value is not None for value in (title, description, footer)):
            raise ValueError(
                "Cannot provide embed together with title, description, or footer."
            )

        if hasattr(embed, "title"):
            title = getattr(embed, "title", None)
            description = getattr(embed, "description", None)
            footer_obj = getattr(embed, "footer", None)
            footer = getattr(footer_obj, "text", None) if footer_obj else None

        if not isinstance(title, str):
            raise ValueError(f"Invalid or missing title: '{title}'")

        if not isinstance(description, str):
            raise ValueError(f"Invalid or missing description: '{description}'")

        if not isinstance(footer, str):
            raise ValueError(f"Invalid or missing footer: '{footer}'")

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
        Safely parse a webhook message without raising any parsing exceptions.

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

        if any(value is not None for value in (title, description, footer)):
            raise ValueError(
                "Cannot provide embed together with title, description, or footer."
            )

        try:
            if embed is not None:
                return self.parse(embed=embed)

            if title is not None and description is not None and footer is not None:
                return self.parse(
                    title=title,
                    description=description,
                    footer=footer,
                )

            return None

        except (ValueError, PRCException):
            return None

    def _get_server(self, *, footer: str) -> Optional["Server"]:
        join_code = self.get_join_code(footer=footer)
        server_id = self._client._global_cache.join_codes.get(join_code)
        if server_id:
            return self._client._global_cache.servers.get(server_id)

    def _get_version(self, *, description: str) -> WebhookVersion:
        if not description:
            raise PRCException(
                f"Cannot get version of empty description: '{description}'"
            )

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
