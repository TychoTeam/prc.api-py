from typing import Literal, Optional, List, Dict, Union, TYPE_CHECKING, cast
from prc.utility import InsensitiveEnum

if TYPE_CHECKING:
    from .server.player import ServerPlayer
    from prc.server import Server
    from prc.client import PRC
    from .player import Player


class Weather(InsensitiveEnum):
    """
    Enum that represents server weather.
    """

    RAIN = "rain"
    THUNDERSTORM = "thunderstorm"
    FOG = "fog"
    CLEAR = "clear"
    SNOW = "snow"


class FireType(InsensitiveEnum):
    """
    Enum that represents a server fire type.
    """

    HOUSE = "house"
    BRUSH = "brush"
    BUILDING = "building"


class CommandTarget:
    """
    Represents a player referenced in a command.

    Parameters
    ----------
    command
        The command where the target was referenced.
    data
        The target's username, partial username or ID.
    author
        The author of the command.
    """

    def __init__(self, command: "Command", data: str, author: "Player"):
        self._client = command._client
        self._server = command._server
        self._author = author

        self.original = data

        self.referenced_name: Optional[str] = None
        self.referenced_id: Optional[int] = None
        if self.original.isdigit() and command.name in _supports_id_targets:
            self.referenced_id = int(self.original)
        elif (
            self.original.lower() in ["me"]
            and command.name in _supports_author_as_target
        ):
            self.referenced_id = author.id
            self.referenced_name = author.name
        else:
            self.referenced_name = self.original

    @property
    def guessed_player(self) -> Optional[Union["ServerPlayer", "Player"]]:
        """
        The closest matched player or server player based on the referenced name or ID. Server players must be fetched separately.
        """

        if self._server:
            return next(
                (
                    player
                    for _, player in self._server._server_cache.players.items()
                    if (
                        player.name.lower().startswith(self.referenced_name.lower())
                        if (self.referenced_name is not None)
                        else (
                            self.referenced_id is not None
                            and player.id == self.referenced_id
                        )
                    )
                ),
                None,
            )
        elif self._client:
            return next(
                (
                    player
                    for _, player in self._client._global_cache.players.items()
                    if (
                        player.name.lower().startswith(self.referenced_name.lower())
                        if (self.referenced_name is not None)
                        else (
                            self.referenced_id is not None
                            and player.id == self.referenced_id
                        )
                    )
                ),
                None,
            )

    def is_author(self, guess: bool = True) -> bool:
        """
        Whether this target is the author of the command.

        Parameters
        ----------
        guess
            Whether to check against the closest matched player (`guessed_player`).
        """

        if self.referenced_id is not None:
            return self._author.id == self.referenced_id
        if guess and self.guessed_player is not None:
            return self._author.id == self.guessed_player.id
        return False

    def is_all(self) -> bool:
        """
        Whether this target references `all`; i.e. affects all players in the server.
        """

        return self.original.lower() in ["all"]

    def is_others(self) -> bool:
        """
        Whether this target references `others`; i.e. affects all players in the server except the command author.
        """

        return self.original.lower() in ["others"]

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.referenced_name}, id={self.referenced_id}>"


class Command:
    """
    Represents a staff-only command.

    Parameters
    ----------
    data
        The full command content.
    author
        The author of the command.
    client
        The global/shared PRC client.
    server
        The server handler, if any.
    is_webhook
        Whether this command is from a webhook message. This will use a different parser for some attributes.
    """

    def __init__(
        self,
        data: str,
        author: "Player",
        client: Optional["PRC"] = None,
        server: Optional["Server"] = None,
        is_webhook: Optional[bool] = False,
    ):
        self._client = client
        self._server = server

        self.full_content: str = data

        parsed_command = self.full_content.split(" ")
        if not parsed_command[0].startswith(":"):
            raise ValueError(f"Malformed command received: {self.full_content}")

        self.name: CommandName = cast(
            CommandName, parsed_command.pop(0).replace(":", "").lower()
        )

        self.targets: Optional[List[CommandTarget]] = None
        if parsed_command and self.name in _supports_targets:
            if self.name in _supports_multi_targets:
                self.targets = []

                if is_webhook:
                    combined = " ".join(parsed_command)
                    parsed_command.clear()

                    parsed_targets = []
                    parts = combined.split(", ")
                    for part in parts:
                        if " " in part:
                            content = part.split(" ")
                            parsed_targets.append(content.pop(0))
                            parsed_command = content
                            break

                        parsed_targets.append(part)

                else:
                    parsed_targets = parsed_command.pop(0).split(",")

                for parsed_target in parsed_targets:
                    if parsed_target:
                        self.targets.append(
                            CommandTarget(
                                self, data=parsed_target.strip(), author=author
                            )
                        )
            else:
                self.targets = [
                    CommandTarget(self, data=parsed_command.pop(0), author=author)
                ]
        elif not parsed_command and self.name in _supports_blank_target:
            self.targets = [CommandTarget(self, data="me", author=author)]

        self.args: Optional[List[CommandArg]] = None
        if parsed_command and self.name in _supports_args:
            self.args = []
            args_count: int = _supports_args.get(self.name, 0)

            while parsed_command and len(self.args) < args_count:
                arg = parsed_command.pop(0)

                if self.name in ["weather"] and Weather.is_member(arg):
                    arg = Weather(arg)
                elif self.name in [
                    "startfire",
                    "startnearfire",
                    "snf",
                ] and FireType.is_member(arg):
                    arg = FireType(arg)
                elif self.name in ["teleport", "tp"]:
                    arg = CommandTarget(self, arg, author=author)
                elif self.name not in [] and arg.isdigit():
                    arg = int(arg)

                if arg:
                    self.args.append(arg)

        self.text = " ".join(parsed_command).strip()
        if not self.text:
            self.text = None

    def __repr__(self) -> str:
        return f"<:{self.name} {self.__class__.__name__}>"


CommandArg = Union[CommandTarget, Weather, FireType, str, int]

CommandName = Literal[
    "kill",
    "killlogs",
    "kl",
    "down",
    "heal",
    "view",
    "spectate",
    "wanted",
    "unwanted",
    "arrest",
    "unjail",
    "jail",
    "free",
    "refresh",
    "respawn",
    "load",
    "bring",
    "teleport",
    "tp",
    "to",
    "tocar",
    "toatv",
    "kick",
    "ban",
    "unban",
    "bans",
    "helper",
    "unhelper",
    "helplers",
    "mod",
    "unmod",
    "mods",
    "moderators",
    "admin",
    "unadmin",
    "admins",
    "administrators",
    "h",
    "hint",
    "m",
    "message",
    "pm",
    "privatemessage",
    "prty",
    "priority",
    "peacetimer",
    "pt",
    "time",
    "startfire",
    "startnearfire",
    "snf",
    "stopfire",
    "log",
    "logs",
    "commands",
    "cmds",
    "weather",
    "loadlayout",
    "unloadlayout",
    "shutdown",
]

_supports_targets: List[CommandName] = [
    "kill",
    "down",
    "heal",
    "view",
    "spectate",
    "wanted",
    "unwanted",
    "arrest",
    "unjail",
    "jail",
    "free",
    "refresh",
    "respawn",
    "load",
    "bring",
    "teleport",
    "tp",
    "to",
    "kick",
    "ban",
    "unban",
    "helper",
    "unhelper",
    "mod",
    "unmod",
    "admin",
    "unadmin",
    "pm",
    "privatemessage",
]

_supports_id_targets: List[CommandName] = [
    "ban",
    "unban",
    "helper",
    "unhelper",
    "mod",
    "unmod",
    "admin",
    "unadmin",
]

_supports_author_as_target: List[CommandName] = [
    "kill",
    "down",
    "heal",
    "view",
    "spectate",
    "wanted",
    "unwanted",
    "arrest",
    "unjail",
    "jail",
    "free",
    "refresh",
    "respawn",
    "load",
    "bring",
    "teleport",
    "tp",
    "to",
    "pm",
    "privatemessage",
]

_supports_blank_target: List[CommandName] = [
    "kill",
    "down",
    "heal",
    "view",
    "spectate",
    "wanted",
    "unwanted",
    "arrest",
    "unjail",
    "jail",
    "free",
    "refresh",
    "respawn",
    "load",
    "bring",
    "to",
]

_supports_multi_targets: List[CommandName] = [
    "kill",
    "down",
    "heal",
    "wanted",
    "unwanted",
    "arrest",
    "unjail",
    "jail",
    "free",
    "refresh",
    "respawn",
    "load",
    "bring",
    "teleport",
    "tp",
    "kick",
    "ban",
    "helper",
    "unhelper",
    "mod",
    "unmod",
    "admin",
    "unadmin",
    "pm",
    "privatemessage",
]

_supports_args: Dict[CommandName, int] = {
    "teleport": 1,
    "tp": 1,
    "prty": 1,
    "priority": 1,
    "peacetimer": 1,
    "pt": 1,
    "time": 1,
    "startfire": 1,
    "startnearfire": 1,
    "snf": 1,
    "weather": 1,
}
