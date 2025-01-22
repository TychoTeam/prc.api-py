from typing import Literal, Optional, List, Dict, Union, TYPE_CHECKING
from prc.utility import InsensitiveEnum

if TYPE_CHECKING:
    from prc.server import Server
    from .logs import LogPlayer


class Weather(InsensitiveEnum):
    """Enum that represents server weather."""

    RAIN = "rain"
    THUNDERSTORM = "thunderstorm"
    FOG = "fog"
    CLEAR = "clear"
    SNOW = "snow"


class FireType(InsensitiveEnum):
    """Enum that represents a server fire type."""

    HOUSE = "house"
    BRUSH = "brush"
    BUILDING = "building"


class CommandTarget:
    """Represents a player referenced in a command."""

    def __init__(
        self, command: "Command", data: str, author: Optional["LogPlayer"] = None
    ):
        self._server = command._server
        self._author = author

        self.original = data

        self.referenced_name: Optional[str] = None
        self.referenced_id: Optional[int] = None
        if self.original.isdigit() and command.name in _supports_id_targets:
            self.referenced_id = int(self.original)
        else:
            if (
                self.original.lower() in ["me"]
                and command.name in _supports_author_as_target
            ):
                self.referenced_id = author.id
                self.referenced_name = author.name
            else:
                self.referenced_name = self.original

    @property
    def guessed_player(self):
        return next(
            (
                player
                for _, player in self._server._server_cache.players.items()
                if (
                    player.name.lower().startswith(self.referenced_name.lower())
                    if self.referenced_name
                    else player.id == self.referenced_id
                )
            ),
            None,
        )

    def is_author(self):
        if self._author is not None and self.referenced_id is not None:
            return self._author.id == self.referenced_id
        return False

    def is_all(self):
        return self.original.lower() in ["all"]

    def is_others(self):
        return self.original.lower() in ["others"]


class Command:
    """Represents a server staff-only command."""

    def __init__(
        self, server: "Server", data: str, author: Optional["LogPlayer"] = None
    ):
        self._server = server

        self.full_content = data

        parsed_command = self.full_content.split(" ")
        if not parsed_command[0].startswith(":"):
            raise ValueError(f"Malformed command received: {self.full_content}")

        self.name: CommandName = parsed_command.pop(0).replace(":", "").lower()

        self.targets: Optional[List[CommandTarget]] = None
        if parsed_command and self.name in _supports_targets:
            if self.name in _supports_multi_targets:
                self.targets = []
                parsed_targets = parsed_command.pop(0).split(",")

                for parsed_target in parsed_targets:
                    if parsed_target:
                        self.targets.append(
                            CommandTarget(self, data=parsed_target, author=author)
                        )
            else:
                self.targets = [
                    CommandTarget(self, data=parsed_command.pop(0), author=author)
                ]
        elif not parsed_command and self.name in _supports_blank_target:
            self.targets = [CommandTarget(self, data="me", author=author)]

        self.args: Optional[List[CommandArg]] = None
        if parsed_command and self.name in _supports_args:
            args_count = _supports_args.get(self.name)
            self.args = []
            for _ in range(args_count):
                if not parsed_command:
                    break
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

        self.text = " ".join(parsed_command)
        if not self.text.strip():
            self.text = None


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
