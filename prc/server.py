from typing import (
    NoReturn,
    Optional,
    List,
    TYPE_CHECKING,
    Callable,
    Type,
    TypeVar,
    Dict,
    Union,
    Sequence,
    Any,
)
from .utility import KeylessCache, Cache, CacheConfig, Requests, InsensitiveEnum
from functools import wraps
from .exceptions import *
from .models import *
import hashlib
import asyncio
import httpx
import copy
import json

from .api_types.v1 import *
from .api_types.v1 import _APIMap

if TYPE_CHECKING:
    from .client import PRC

R = TypeVar("R")
M = TypeVar("M")
LOG = TypeVar("LOG")


class ServerCache:
    """
    Server long-term object caches and config. TTL in seconds, 0 to disable. (max_size, TTL)
    """

    def __init__(
        self,
        players: CacheConfig = (50, 0),
        vehicles: CacheConfig = (100, 1 * 60 * 60),
        access_logs: CacheConfig = (150, 6 * 60 * 60),
    ):
        self.players = Cache[int, ServerPlayer](*players)
        self.vehicles = KeylessCache[Vehicle](*vehicles)
        self.access_logs = KeylessCache[AccessEntry](
            *access_logs, sort=(lambda e: e.created_at, True)
        )


def _refresh_server(func):
    async def wrapper(self: "Server", *args, **kwargs):
        server = self._server if isinstance(self, ServerModule) else self
        result = await func(self, *args, **kwargs)
        self._global_cache.servers.set(server._id, server)
        return result

    return wrapper


def _ephemeral(func):
    @wraps(func)
    async def wrapper(self: "Server", *args, **kwargs):
        try:
            args_repr = json.dumps(args, sort_keys=True, default=str)
            kwargs_repr = json.dumps(kwargs, sort_keys=True, default=str)
        except (TypeError, ValueError):
            args_repr = str(args)
            kwargs_repr = str(kwargs)

        hashed_args = hashlib.sha256(f"{args_repr}|{kwargs_repr}".encode()).hexdigest()
        cache_key = f"{func.__name__}_cache_{hashed_args}"

        if hasattr(self, cache_key):
            cached_result, timestamp = getattr(self, cache_key)
            if (asyncio.get_event_loop().time() - timestamp) < self._ephemeral_ttl:
                return copy.copy(cached_result)

        result = await func(self, *args, **kwargs)
        setattr(self, cache_key, (result, asyncio.get_event_loop().time()))
        return copy.copy(result)

    return wrapper


class Server:
    """
    The main class to interface with PRC ER:LC server APIs.

    Parameters
    ----------
    client
        The global/shared PRC client.
    server_key
        The unique server key used to authenticate requests.
    ephemeral_ttl
        How long, in seconds, ephemeral results (i.e. cached responses) are kept before expiring. Defaults to `3` seconds.
    cache
        An initialized server cache to use. By default, a new instance is created.
    requests
        An initialized requests class. By default, a new instance is created.
    ignore_global_key
        Whether to ignore the client's global authentication key (if set). By default, it is not ignored.
    """

    def __init__(
        self,
        client: "PRC",
        server_key: str,
        ephemeral_ttl: int = 3,
        cache: ServerCache = ServerCache(),
        requests: Optional[Requests] = None,
        ignore_global_key: bool = False,
    ):
        self._client = client

        client._validate_server_key(server_key)
        self._id = client._get_server_id(server_key)

        self._global_cache = client._global_cache
        self._server_cache = cache
        self._ephemeral_ttl = ephemeral_ttl

        self._global_key = client._global_key
        self._server_key = server_key
        self._ignore_global_key = ignore_global_key
        self._requests: Requests[
            Literal[
                "/",
                "/players",
                "/queue",
                "/bans",
                "/vehicles",
                "/staff",
                "/joinlogs",
                "/killlogs",
                "/commandlogs",
                "/modcalls",
                "/command",
            ]
        ] = (
            requests or self._refresh_requests()
        )

        self.logs = ServerLogs(self)
        self.commands = ServerCommands(self)

    name: Optional[str] = None
    owner: Optional[ServerOwner] = None
    co_owners: List[ServerOwner] = []
    admins: List[StaffMember] = []
    mods: List[StaffMember] = []
    total_staff_count: Optional[int] = None
    player_count: Optional[int] = None
    staff_count: Optional[int] = None
    queue_count: Optional[int] = None
    max_players: Optional[int] = None
    join_code: Optional[str] = None
    account_requirement: Optional[AccountRequirement] = None
    team_balance: Optional[bool] = None

    @property
    def join_link(self) -> Optional[str]:
        """
        Web URL that allows users to join the game and queue automatically for the server.
        Hosted by PRC. Server status must be fetched separately. ⚠️ *(May not function properly on mobile devices -- May not function at random times)*
        """

        return (
            ("https://policeroleplay.community/join/" + self.join_code)
            if self.join_code
            else None
        )

    def is_online(self) -> Optional[bool]:
        """
        Whether the server is online (i.e. has any online players). Server status or players must be fetched separately.
        """

        return self.player_count > 0 if self.player_count else None

    def is_full(self, include_reserved: bool = False) -> Optional[bool]:
        """
        Whether the server player count has reached the max player limit. Server status must be fetched separately.

        Parameters
        ----------
        include_reserved
            Whether to include the owner-reserved spot. By default, it is excluded (`max_players - 1`).
        """

        return (
            (self.player_count >= self.max_players - (0 if include_reserved else 1))
            if self.player_count and self.max_players
            else None
        )

    def _refresh_requests(self):
        global_key = self._global_key
        headers = {"Server-Key": self._server_key}
        if global_key and not self._ignore_global_key:
            headers["Authorization"] = global_key
        self._requests = Requests(
            base_url=self._client._base_url + "/server",
            headers=headers,
            session=self._client._session,
            invalid_keys=self._global_cache.invalid_keys,
        )
        return self._requests

    def _parse_api_map(self, map: _APIMap[M]) -> Dict[str, M]:
        if not isinstance(map, Dict):
            return {}
        return map

    def _get_player(
        self, *, id: Optional[int] = None, name: Optional[str] = None
    ) -> Optional[ServerPlayer]:
        for _, player in self._server_cache.players.items():
            if id and player.id == id:
                return player
            if name and player.name == name:
                return player

    def _raise_error_code(self, response: Any) -> NoReturn:
        if not isinstance(response, Dict):
            raise PRCException("A malformed response was received.")

        error_code = response.get("code")
        if error_code is None:
            raise PRCException("No error code was received.")

        exceptions: List[Callable[..., APIException]] = [
            UnknownError,
            CommunicationError,
            InternalError,
            InvalidServerKey,
            InvalidGlobalKey,
            BannedServerKey,
            InvalidCommand,
            ServerOffline,
            RateLimited,
            RestrictedCommand,
            ProhibitedMessage,
            RestrictedResource,
            OutOfDateModule,
        ]

        for _exception in exceptions:
            exception = _exception()
            if error_code == exception.code:
                invalid_key = None
                if isinstance(exception, InvalidGlobalKey):
                    invalid_key = self._global_key
                elif isinstance(exception, (InvalidServerKey, BannedServerKey)):
                    invalid_key = self._server_key

                if invalid_key:
                    self._global_cache.invalid_keys.add(invalid_key)

                if isinstance(exception, RateLimited):
                    exception = RateLimited(
                        response.get("bucket"), response.get("retry_after")
                    )

                if isinstance(exception, (CommunicationError, ServerOffline)):
                    exception = _exception(command_id=response.get("commandId"))

                raise exception

        raise APIException(
            error_code,
            f"An unknown API error has occured: {response.get('message') or '...'}",
        )

    def _handle(self, response: httpx.Response, return_type: Type[R]) -> R:
        content_type: Optional[str] = response.headers.get("Content-Type", None)
        if not content_type or not content_type.startswith("application/json"):
            raise PRCException(f"Received a non-json content type: '{content_type}'")

        if not response.is_success:
            self._raise_error_code(response.json())
        return response.json()

    @_refresh_server
    @_ephemeral
    async def get_status(self) -> ServerStatus:
        """
        Get the current server status.
        """

        return ServerStatus(
            self,
            data=self._handle(await self._requests.get("/"), v1_ServerStatusResponse),
        )

    @_refresh_server
    @_ephemeral
    async def get_players(self) -> List[ServerPlayer]:
        """
        Get all online server players.
        """

        self._server_cache.players.clear()
        players = [
            ServerPlayer(self, data=p)
            for p in self._handle(
                await self._requests.get("/players"), v1_ServerPlayersResponse
            )
        ]
        self.player_count = len(players)
        self.staff_count = len([p for p in players if p.is_staff()])
        return players

    @_refresh_server
    @_ephemeral
    async def get_queue(self) -> List[QueuedPlayer]:
        """
        Get all players in the server join queue.
        """

        players = [
            QueuedPlayer(self, id=p, index=i)
            for i, p in enumerate(
                self._handle(await self._requests.get("/queue"), v1_ServerQueueResponse)
            )
        ]
        self.queue_count = len(players)
        return players

    @_refresh_server
    @_ephemeral
    async def get_bans(self) -> List[Player]:
        """
        Get all banned players.
        """

        return [
            Player(self._client, data=p, _skip_cache=True)
            for p in self._parse_api_map(
                self._handle(await self._requests.get("/bans"), v1_ServerBanResponse)
            ).items()
        ]

    @_refresh_server
    @_ephemeral
    async def get_vehicles(self) -> List[Vehicle]:
        """
        Get all spawned vehicles in the server. A single server player may have up to 2 spawned vehicles (1 primary + 1 secondary).
        """

        self._server_cache.vehicles.clear()
        return [
            Vehicle(self, data=v)
            for v in self._handle(
                await self._requests.get("/vehicles"), v1_ServerVehiclesResponse
            )
        ]

    @_refresh_server
    @_ephemeral
    async def get_staff(self) -> ServerStaff:
        """
        Get all server staff members excluding server owner. ⚠️ *(This endpoint is deprecated, use at your own risk)*
        """

        return ServerStaff(
            self,
            data=self._handle(
                await self._requests.get("/staff"), v1_ServerStaffResponse
            ),
        )


class ServerModule:
    """
    A class implemented by modules used by the main `Server` class to interface with specific PRC ER:LC server APIs.
    """

    def __init__(self, server: Server):
        self._server = server

        self._global_cache = server._global_cache
        self._server_cache = server._server_cache
        self._ephemeral_ttl = server._ephemeral_ttl

        self._requests = server._requests
        self._handle = server._handle


class ServerLogs(ServerModule):
    """
    Interact with PRC ER:LC server logs APIs.
    """

    def __init__(self, server: Server):
        super().__init__(server)

    def _sort(self, logs: Sequence[LOG], oldest_first: bool = False) -> List[LOG]:
        return sorted(
            logs, key=lambda x: getattr(x, "created_at"), reverse=not oldest_first
        )

    @_refresh_server
    @_ephemeral
    async def get_access(self, *, oldest_first: bool = False) -> List[AccessEntry]:
        """
        Get server access (join/leave) logs.

        Parameters
        ----------
        oldest_first
            Whether to return older logs first. By default, newer logs come first.
        """

        for e in self._handle(
            await self._requests.get("/joinlogs"), v1_ServerJoinLogsResponse
        ):
            AccessEntry(self._server, data=e)
        return self._sort(self._server_cache.access_logs.items(), oldest_first)

    @_refresh_server
    @_ephemeral
    async def get_kills(self, *, oldest_first: bool = False) -> List[KillEntry]:
        """
        Get server kill logs.

        Parameters
        ----------
        oldest_first
            Whether to return older logs first. By default, newer logs come first.
        """

        return self._sort(
            [
                KillEntry(self._server, data=e)
                for e in self._handle(
                    await self._requests.get("/killlogs"), v1_ServerKillLogsResponse
                )
            ],
            oldest_first,
        )

    @_refresh_server
    @_ephemeral
    async def get_commands(self, *, oldest_first: bool = False) -> List[CommandEntry]:
        """
        Get server command usage logs.

        Parameters
        ----------
        oldest_first
            Whether to return older logs first. By default, newer logs come first.
        """

        return self._sort(
            [
                CommandEntry(self._server, data=e)
                for e in self._handle(
                    await self._requests.get("/commandlogs"),
                    v1_ServerCommandLogsResponse,
                )
            ],
            oldest_first,
        )

    @_refresh_server
    @_ephemeral
    async def get_mod_calls(self, *, oldest_first: bool = False) -> List[ModCallEntry]:
        """
        Get server mod call logs.

        Parameters
        ----------
        oldest_first
            Whether to return older logs first. By default, newer logs come first.
        """

        return self._sort(
            [
                ModCallEntry(self._server, data=e)
                for e in self._handle(
                    await self._requests.get("/modcalls"), v1_ServerModCallsResponse
                )
            ],
            oldest_first,
        )


CommandTargetPlayerName = Union[str, Player]
CommandTargetPlayerId = Union[int, Player]
CommandTargetPlayerNameOrId = Union[CommandTargetPlayerName, CommandTargetPlayerId]


class ServerCommands(ServerModule):
    """
    Interact with the PRC ER:LC server remote command execution API.
    """

    def __init__(self, server: Server):
        super().__init__(server)

    async def _raw(self, command: str):
        """
        Send an **UNSANITIZED** command string to the remote command execution API.

        Parameters
        ----------
        command
            The full command content string to send.
        """

        return self._handle(
            await self._requests.post("/command", json={"command": command}),
            v1_ServerCommandExecutionResponse,
        )

    async def run(
        self,
        name: CommandName,
        *,
        targets: Optional[Sequence[CommandTargetPlayerNameOrId]] = None,
        args: Optional[List[Union[CommandArg, Player]]] = None,
        text: Optional[str] = None,
        _max_retries: int = 3,
        _prefer_player_id: bool = False,
    ) -> None:
        """
        Run any command as the remote player in the server.

        Parameters
        ----------
        targets
            Players to be targeted by the command.
        args
            Specific command arguments (e.g. weather, fire type).
        text
            Any text to be sent along the command (e.g. reason, announcement message content).
        """

        command = f":{name} "

        def parse_target(target: CommandTargetPlayerNameOrId):
            if isinstance(target, Player):
                if _prefer_player_id:
                    return str(target.id)
                return str(target.name)
            return str(target)

        def parse_arg(arg: Union[CommandArg, Player]):
            if isinstance(arg, Player):
                if _prefer_player_id:
                    return str(arg.id)
                return str(arg.name)
            if isinstance(arg, InsensitiveEnum):
                return arg.value
            return str(arg)

        if targets:
            command += ",".join([parse_target(t) for t in targets]) + " "

        if args:
            command += " ".join([parse_arg(a) for a in args]) + " "

        if text:
            command += text

        message = "..."
        success = False
        retry = 0

        while success == False and retry < _max_retries:
            message = (await self._raw(command.strip())).get("message")
            success = message == "Success"
            retry += 1

        if not success:
            raise PRCException(
                f"Command execution has unexpectedly failed: '{message}'"
            )

    async def kill(self, targets: List[CommandTargetPlayerName]):
        """
        Kill players in the server.

        Parameters
        ----------
        targets
            The players to kill. A player can be a username, partial username or a player (and any of its subclasses).
        """

        await self.run("kill", targets=targets)

    async def heal(self, targets: List[CommandTargetPlayerName]):
        """
        Heal players in the server.

        Parameters
        ----------
        targets
            The players to heal. A player can be a username, partial username or a player (and any of its subclasses).
        """

        await self.run("heal", targets=targets)

    async def make_wanted(self, targets: List[CommandTargetPlayerName]):
        """
        Make players wanted in the server.

        Parameters
        ----------
        targets
            The players to make wanted. A player can be a username, partial username or a player (and any of its subclasses).
        """

        await self.run("wanted", targets=targets)

    async def remove_wanted(self, targets: List[CommandTargetPlayerName]):
        """
        Remove wanted status from players in the server.

        Parameters
        ----------
        targets
            The players to remove wanted status from. A player can be a username, partial username or a player (and any of its subclasses).
        """

        await self.run("unwanted", targets=targets)

    async def make_jailed(self, targets: List[CommandTargetPlayerName]):
        """
        Make players jailed in the server. Teleports them to a prison cell and changes the server player's team.

        Parameters
        ----------
        targets
            The players to make jailed. A player can be a username, partial username or a player (and any of its subclasses).
        """

        await self.run("jail", targets=targets)

    async def remove_jailed(self, targets: List[CommandTargetPlayerName]):
        """
        Remove jailed status from players in the server.

        Parameters
        ----------
        targets
            The players to remove jail status from. A player can be a username, partial username or a player (and any of its subclasses).
        """

        await self.run("unjail", targets=targets)

    async def refresh(self, targets: List[CommandTargetPlayerName]):
        """
        Respawn players in the server and return them to their last positions.

        Parameters
        ----------
        targets
            The players to refresh. A player can be a username, partial username or a player (and any of its subclasses).
        """

        await self.run("refresh", targets=targets)

    async def respawn(self, targets: List[CommandTargetPlayerName]):
        """
        Respawn players in the server and return them to their set spawn location.

        Parameters
        ----------
        targets
            The players to respawn. A player can be a username, partial username or a player (and any of its subclasses).
        """

        await self.run("load", targets=targets)

    async def teleport(
        self, targets: List[CommandTargetPlayerName], *, to: CommandTargetPlayerName
    ):
        """
        Teleport players to another player in the server.

        Parameters
        ----------
        targets
            The players to teleport. A player can be a username, partial username or a player (and any of its subclasses).
        to
            The player to be teleported to. A player can be a username, partial username or a player (and any of its subclasses).
        """

        await self.run("tp", targets=targets, args=[to])

    async def kick(
        self, targets: List[CommandTargetPlayerName], *, reason: Optional[str] = None
    ):
        """
        Kick players from the server.

        Parameters
        ----------
        targets
            The players to kick. A player can be a username, partial username or a player (and any of its subclasses).
        reason
            The reason for the kick, if any.
        """

        await self.run("kick", targets=targets, text=reason)

    async def ban(self, targets: List[CommandTargetPlayerNameOrId]):
        """
        Ban players from the server.

        Parameters
        ----------
        targets
            The players to ban. A player can be a username, partial username, ID or a player (and any of its subclasses).
        """

        await self.run("ban", targets=targets, _prefer_player_id=True)

    async def unban(self, targets: List[CommandTargetPlayerNameOrId]):
        """
        Unban players from the server.

        Parameters
        ----------
        targets
            The players to unban. A player can be a username, ID or a player (and any of its subclasses).
        """

        await self.run("unban", targets=targets, _prefer_player_id=True)

    async def shutdown(self):
        """
        Shutdown the server. Kicks all players in-game.
        """

        await self.run("shutdown")

    async def grant_helper(self, targets: List[CommandTargetPlayerNameOrId]):
        """
        Grant helper permissions to players in the server.

        Parameters
        ----------
        targets
            The players to grant permissions to. A player can be a username, partial username, ID or a player (and any of its subclasses).
        """

        await self.run("helper", targets=targets, _prefer_player_id=True)

    async def revoke_helper(self, targets: List[CommandTargetPlayerNameOrId]):
        """
        Revoke helper permissions to players in the server.

        Parameters
        ----------
        targets
            The players to revoke permissions from. A player can be a username, partial username, ID or a player (and any of its subclasses).
        """

        await self.run("unhelper", targets=targets, _prefer_player_id=True)

    async def grant_mod(self, targets: List[CommandTargetPlayerNameOrId]):
        """
        Grant moderator permissions to players in the server.

        Parameters
        ----------
        targets
            The players to grant permissions to. A player can be a username, partial username, ID or a player (and any of its subclasses).
        """

        await self.run("mod", targets=targets, _prefer_player_id=True)

    async def revoke_mod(self, targets: List[CommandTargetPlayerNameOrId]):
        """
        Revoke moderator permissions from players in the server.

        Parameters
        ----------
        targets
            The players to revoke permissions from. A player can be a username, partial username, ID or a player (and any of its subclasses).
        """

        await self.run("unmod", targets=targets, _prefer_player_id=True)

    async def grant_admin(self, targets: List[CommandTargetPlayerNameOrId]):
        """
        Grant admin permissions to players in the server.

        Parameters
        ----------
        targets
            The players to grant permissions to. A player can be a username, partial username, ID or a player (and any of its subclasses).
        """

        await self.run("admin", targets=targets, _prefer_player_id=True)

    async def revoke_admin(self, targets: List[CommandTargetPlayerNameOrId]):
        """
        Revoke admin permissions from players in the server.

        Parameters
        ----------
        targets
            The players to revoke permissions from. A player can be a username, partial username, ID or a player (and any of its subclasses).
        """

        await self.run("unadmin", targets=targets, _prefer_player_id=True)

    async def send_hint(self, text: str):
        """
        Send a temporary message to the server (undismissable banner).

        Parameters
        ----------
        text
            The hint message content.
        """

        await self.run("h", text=text)

    async def send_announcement(self, text: str):
        """
        Send an announcement message to the server (dismissable popup).

        Parameters
        ----------
        text
            The announcement message content.
        """

        await self.run("m", text=text)

    async def send_pm(self, targets: List[CommandTargetPlayerName], text: str):
        """
        Send a private message to players in the server (dismissable popup).

        Parameters
        ----------
        targets
            The players to message. A player can be a username, partial username or a player (and any of its subclasses).
        text
            The private message content.
        """

        await self.run("pm", targets=targets, text=text)

    async def send_log(self, text: str):
        """
        Emit a custom string that will be saved in command logs and sent to configured command usage webhooks (if any) using the `log` command. Mostly used for integrating with other applications.

        Parameters
        ----------
        text
            The custom string to emit.
        """

        await self.run("log", text=text)

    async def set_priority(self, *, seconds: int = 0):
        """
        Set the server priority timer. Shows an undismissable countdown notification to all players until it reaches `0`.

        Parameters
        ----------
        seconds
            The priority timer duration in seconds. Leave empty or set to `0` to disable.
        """

        await self.run("prty", args=[seconds])

    async def set_peace(self, *, seconds: int = 0):
        """
        Set the server peace timer. Shows an undismissable countdown notification to all players until it reaches `0` while disabling PVP damage.

        Parameters
        ----------
        seconds
            The peace timer duration in seconds. Leave empty or set to `0` to disable.
        """

        await self.run("pt", args=[seconds])

    async def set_time(self, hour: int):
        """
        Set the current server time of day as the given hour. Uses 24-hour formatting.

        Parameters
        ----------
        hour
            The hour of day to set (`12` = noon, `0`/`24` = midnight).
        """

        await self.run("time", args=[hour])

    async def set_weather(self, type: Weather):
        """
        Set the current server weather.

        Parameters
        ----------
        type
            The type of weather to set. `SNOW` can only be set during winter.
        """

        await self.run("weather", args=[type])

    async def start_fire(self, type: FireType):
        """
        Start a fire at a random location in the server.

        Parameters
        ----------
        type
            The type of fire to start.
        """

        await self.run("startfire", args=[type])

    async def stop_fires(self):
        """
        Stop all fires in the server.
        """

        await self.run("stopfire")

    async def load_layout(self, key: str):
        """
        Load a map editor layout (aka. map template).

        Parameters
        ----------
        key
            The custom layout name or public share code.
        """

        await self.run("loadlayout", text=key)

    async def unload_layout(self, key: str):
        """
        Unload a map editor layout (aka. map template).

        Parameters
        ----------
        key
            The custom layout name or public share code.
        """

        await self.run("unloadlayout", text=key)
