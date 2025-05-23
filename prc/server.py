from typing import (
    Optional,
    List,
    TYPE_CHECKING,
    Callable,
    Type,
    TypeVar,
    Dict,
    Union,
    Literal,
    Sequence,
)
from .utility import KeylessCache, Cache, CacheConfig, Requests, InsensitiveEnum
from .utility.exceptions import *
from .models import *
import asyncio
import httpx

from .api_types.v1 import *

if TYPE_CHECKING:
    from .client import PRC

R = TypeVar("R")


class ServerCache:
    """Server long-term object caches and config. TTL in seconds, 0 to disable. (max_size, TTL)"""

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
    async def wrapper(self: "Server", *args, **kwargs):
        cache_key = f"{func.__name__}_cache"
        if hasattr(self, cache_key):
            cached_result, timestamp = getattr(self, cache_key)
            if (asyncio.get_event_loop().time() - timestamp) < self._ephemeral_ttl:
                return cached_result

        result = await func(self, *args, **kwargs)
        setattr(self, cache_key, (result, asyncio.get_event_loop().time()))
        return result

    return wrapper


class Server:
    """The main class to interface with PRC ER:LC server APIs. `ephemeral_ttl` is how long, in seconds, results are cached for."""

    def __init__(
        self,
        client: "PRC",
        server_key: str,
        ephemeral_ttl: int = 5,
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

        global_key = client._global_key
        headers = {"Server-Key": server_key}
        if global_key and not ignore_global_key:
            headers["Authorization"] = global_key
        self._requests = requests or Requests(
            base_url=client._base_url + "/server",
            headers=headers,
            session=client._session,
        )
        self._ignore_global_key = ignore_global_key

        self.logs = ServerLogs(self)
        self.commands = ServerCommands(self)

    name: Optional[str] = None
    owner: Optional[ServerOwner] = None
    co_owners: List[ServerOwner] = []
    player_count: Optional[int] = None
    staff_count: Optional[int] = None
    queue_count: Optional[int] = None
    max_players: Optional[int] = None
    join_code: Optional[str] = None
    account_requirement: Optional[AccountRequirement] = None
    team_balance: Optional[bool] = None

    @property
    def join_link(self):
        """Web URL that allows users to join the game and queue automatically for the server. Hosted by PRC. Server status must be fetched separately. ⚠️ *(May not function properly on mobile devices -- May not function at random times)*"""
        return (
            ("https://policeroleplay.community/join/" + self.join_code)
            if self.join_code
            else None
        )

    def _get_player(self, id: Optional[int] = None, name: Optional[str] = None):
        for _, player in self._server_cache.players.items():
            if id and player.id == id:
                return player
            if name and player.name == name:
                return player

    def _handle_error_code(self, error_code: Optional[int] = None):
        if error_code is None:
            raise PRCException("An unknown error has occured.")

        errors: List[Callable[..., APIException]] = [
            UnknownError,
            CommunicationError,
            InternalError,
            MissingServerKey,
            InvalidServerKeyFormat,
            InvalidServerKey,
            InvalidGlobalKey,
            BannedServerKey,
            InvalidCommand,
            ServerOffline,
            RateLimit,
            RestrictedCommand,
            ProhibitedMessage,
            RestrictedResource,
            OutOfDateModule,
        ]

        for error in errors:
            error = error()
            if error_code == error.error_code:
                invalid_key = None
                if isinstance(error, InvalidGlobalKey):
                    invalid_key = self._requests._default_headers.get("Authorization")
                elif isinstance(error, (InvalidServerKey, BannedServerKey)):
                    invalid_key = self._requests._default_headers.get("Server-Key")

                if invalid_key:
                    self._requests._invalid_keys.add(invalid_key)

                raise error

        raise APIException(error_code, "An unknown API error has occured.")

    def _handle(self, response: httpx.Response, return_type: Type[R]) -> R:
        if not response.is_success:
            self._handle_error_code((response.json() or {}).get("code"))
        return response.json()

    @_refresh_server
    @_ephemeral
    async def get_status(self):
        """Get the current server status."""
        return ServerStatus(
            self, data=self._handle(await self._requests.get("/"), ServerStatusResponse)
        )

    @_refresh_server
    @_ephemeral
    async def get_players(self):
        """Get all online server players."""
        players = [
            ServerPlayer(self, data=p)
            for p in self._handle(
                await self._requests.get("/players"), List[ServerPlayerResponse]
            )
        ]
        self.player_count = len(players)
        self.staff_count = len([p for p in players if p.is_staff()])
        return players

    @_ephemeral
    async def get_queue(self):
        """Get all players in the server join queue."""
        players = [
            QueuedPlayer(self, id=p, index=i)
            for i, p in enumerate(
                self._handle(await self._requests.get("/queue"), List[int])
            )
        ]
        self.queue_count = len(players)
        return players

    @_refresh_server
    @_ephemeral
    async def get_bans(self):
        """Get all banned players."""
        return [
            Player(self._client, data=p)
            for p in (
                self._handle(await self._requests.get("/bans"), ServerBanResponse) or {}
            ).items()
        ]

    @_refresh_server
    @_ephemeral
    async def get_vehicles(self):
        """Get all spawned vehicles in the server. A server player may have 2 spawned vehicles (1 primary + 1 secondary)."""
        return [
            Vehicle(self, data=v)
            for v in self._handle(
                await self._requests.get("/vehicles"), List[ServerVehicleResponse]
            )
        ]


class ServerModule:
    """A class implemented by modules used by the main `Server` class to interface with specific PRC ER:LC server APIs."""

    def __init__(self, server: Server):
        self._server = server

        self._global_cache = server._global_cache
        self._server_cache = server._server_cache
        self._ephemeral_ttl = server._ephemeral_ttl

        self._requests = server._requests
        self._handle = server._handle


class ServerLogs(ServerModule):
    """Interact with PRC ER:LC server logs APIs."""

    def __init__(self, server: Server):
        super().__init__(server)

    @_refresh_server
    @_ephemeral
    async def get_access(self):
        """Get server access (join/leave) logs."""
        [
            AccessEntry(self._server, data=e)
            for e in self._handle(
                await self._requests.get("/joinlogs"), List[ServerJoinLogResponse]
            )
        ]
        return self._server_cache.access_logs.items()

    @_refresh_server
    @_ephemeral
    async def get_kills(self):
        """Get server kill logs."""
        return [
            KillEntry(self._server, data=e)
            for e in self._handle(
                await self._requests.get("/killlogs"), List[ServerKillLogResponse]
            )
        ]

    @_refresh_server
    @_ephemeral
    async def get_commands(self):
        """Get server command logs."""
        return [
            CommandEntry(self._server, data=e)
            for e in self._handle(
                await self._requests.get("/commandlogs"), List[ServerCommandLogResponse]
            )
        ]

    @_refresh_server
    @_ephemeral
    async def get_mod_calls(self):
        """Get server mod call logs."""
        return [
            ModCallEntry(self._server, data=e)
            for e in self._handle(
                await self._requests.get("/modcalls"), List[ServerModCallResponse]
            )
        ]


CommandTargetPlayerName = str
CommandTargetPlayerID = int
CommandTargetPlayerNameOrID = Union[CommandTargetPlayerName, CommandTargetPlayerID]


class ServerCommands(ServerModule):
    """Interact with the PRC ER:LC server remote command execution API."""

    def __init__(self, server: Server):
        super().__init__(server)

    async def _raw(self, command: str):
        """Run a raw string command as the remote player in the server."""
        return self._handle(
            await self._requests.post("/command", json={"command": command}),
            Dict,
        )

    async def run(
        self,
        name: CommandName,
        targets: Optional[Sequence[CommandTargetPlayerNameOrID]] = None,
        args: Optional[List[CommandArg]] = None,
        text: Optional[str] = None,
    ):
        """Run any command as the remote player in the server."""
        command = f":{name} "

        if targets:
            command += ",".join([str(t) for t in targets]) + " "

        if args:
            command += (
                " ".join(
                    [
                        (a.value if isinstance(a, InsensitiveEnum) else str(a))
                        for a in args
                    ]
                )
                + " "
            )

        if text:
            command += text

        await self._raw(command.strip())

    async def kill(self, targets: List[CommandTargetPlayerName]):
        """Kill players in the server."""
        await self.run("kill", targets=targets)

    async def heal(self, targets: List[CommandTargetPlayerName]):
        """Heal players in the server."""
        await self.run("heal", targets=targets)

    async def wanted(self, targets: List[CommandTargetPlayerName]):
        """Make players wanted in the server."""
        await self.run("wanted", targets=targets)

    async def unwanted(self, targets: List[CommandTargetPlayerName]):
        """Remove wanted status from players in the server."""
        await self.run("unwanted", targets=targets)

    async def jail(self, targets: List[CommandTargetPlayerName]):
        """Jail players in the server."""
        await self.run("jail", targets=targets)

    async def unjail(self, targets: List[CommandTargetPlayerName]):
        """Remove jailed status from players in the server."""
        await self.run("unjail", targets=targets)

    async def refresh(self, targets: List[CommandTargetPlayerName]):
        """Respawn players in the server and return them to their last positions."""
        await self.run("refresh", targets=targets)

    async def respawn(self, targets: List[CommandTargetPlayerName]):
        """Respawn players in the server and return them to their set spawn location."""
        await self.run("load", targets=targets)

    async def teleport(self, targets: List[CommandTargetPlayerName], to: str):
        """Teleport players to another player in the server."""
        await self.run("tp", targets=targets, args=[to])

    async def kick(
        self,
        targets: List[CommandTargetPlayerName],
        reason: Optional[str] = None,
    ):
        """Kick players from the server."""
        await self.run("kick", targets=targets, text=reason)

    async def ban(self, targets: List[CommandTargetPlayerNameOrID]):
        """Ban players from the server."""
        await self.run("ban", targets=targets)

    async def unban(self, targets: List[CommandTargetPlayerNameOrID]):
        """Unban players from the server."""
        await self.run("unban", targets=targets)

    async def helper(self, targets: List[CommandTargetPlayerNameOrID]):
        """Grant helper permissions to players in the server."""
        await self.run("helper", targets=targets)

    async def unhelper(self, targets: List[CommandTargetPlayerNameOrID]):
        """Revoke helper permissions to players in the server."""
        await self.run("unhelper", targets=targets)

    async def mod(self, targets: List[CommandTargetPlayerNameOrID]):
        """Grant moderator permissions to players in the server."""
        await self.run("mod", targets=targets)

    async def unmod(self, targets: List[CommandTargetPlayerNameOrID]):
        """Revoke moderator permissions from players in the server."""
        await self.run("unmod", targets=targets)

    async def admin(self, targets: List[CommandTargetPlayerNameOrID]):
        """Grant admin permissions to players in the server."""
        await self.run("admin", targets=targets)

    async def unadmin(self, targets: List[CommandTargetPlayerNameOrID]):
        """Revoke admin permissions from players in the server."""
        await self.run("unadmin", targets=targets)

    async def hint(self, text: str):
        """Send a temporary message to the server (undismissable banner)."""
        await self.run("h", text=text)

    async def announce(self, text: str):
        """Send an announcement message to the server (dismissable popup)."""
        await self.run("m", text=text)

    async def pm(self, targets: List[CommandTargetPlayerName], text: str):
        """Send a private message to players in the server (dismissable popup)."""
        await self.run("pm", targets=targets, text=text)

    async def log(self, text: str):
        """Send a customizable string that will be saved in command logs and sent to configured command usage webhooks (if any). Uses the `:log` command."""
        await self.run("log", text=text)

    async def set_priority(self, seconds: int = 0):
        """Set the server priority timer. Shows an undismissable countdown notification to all players until it reaches `0`. Leave empty or set to `0` to disable."""
        await self.run("prty", args=[seconds])

    async def set_peace(self, seconds: int = 0):
        """Set the server peace timer. Shows an undismissable countdown notification to all players until it reaches `0` while disabling PVP damage. Leave empty or set to `0` to disable."""
        await self.run("pt", args=[seconds])

    async def set_time(self, hour: int):
        """Set the current server time of day as the given hour. Uses 24-hour formatting (`12` = noon, `0`/`24` = midnight)."""
        await self.run("time", args=[hour])

    async def set_weather(self, type: Weather):
        """Set the current server weather. `Weather.SNOW` can only be set during winter."""
        await self.run("weather", args=[type])

    async def start_fire(self, type: FireType):
        """Start a fire at a random location in the server."""
        await self.run("startfire", args=[type])

    async def stop_fires(self):
        """Stop all fires in the server."""
        await self.run("stopfire")
