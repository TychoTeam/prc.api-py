from typing import Optional, List, TYPE_CHECKING, Callable, Type, TypeVar, Dict, Union
from .utility import KeylessCache, Cache, CacheConfig, Requests, InsensitiveEnum
from .utility.exceptions import *
from .models import *
import asyncio
import httpx

if TYPE_CHECKING:
    from .client import PRC

R = TypeVar("R")


class ServerCache:
    """Server long-term object caches and config. TTL in seconds, 0 to disable. (max_size, TTL)"""

    def __init__(
        self,
        players: CacheConfig = (50, 0),
        bans: CacheConfig = (500, 0),
        vehicles: CacheConfig = (50, 1 * 60 * 60),
        join_logs: CacheConfig = (100, 12 * 60 * 60),
        kill_logs: CacheConfig = (100, 12 * 60 * 60),
        command_logs: CacheConfig = (100, 12 * 60 * 60),
        mod_call_logs: CacheConfig = (100, 12 * 60 * 60),
    ):
        self.players = Cache[int, ServerPlayer](*players)
        self.bans = Cache[int, Player](*bans)
        self.vehicles = KeylessCache[Vehicle](*vehicles)

        self.join_logs = KeylessCache[JoinEntry](
            *join_logs, sort=(lambda e: e.created_at, True)
        )
        self.kill_logs = KeylessCache[KillEntry](
            *kill_logs, sort=(lambda e: e.created_at, True)
        )
        self.command_logs = KeylessCache[CommandEntry](
            *command_logs, sort=(lambda e: e.created_at, True)
        )
        self.mod_call_logs = KeylessCache[ModCallEntry](
            *mod_call_logs, sort=(lambda e: e.created_at, True)
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
    ):
        self._client = client

        client._validate_server_key(server_key)
        self._id = client._get_server_id(server_key)

        self._global_cache = client._global_cache
        self._server_cache = cache
        self._ephemeral_ttl = ephemeral_ttl

        global_key = client._global_key
        headers = {"Server-Key": server_key}
        if global_key:
            headers["Authorization"] = global_key
        self._requests = requests or Requests(
            base_url=client._base_url + "/server", headers=headers
        )

        self.logs = ServerLog(self)

    name: Optional[str] = None
    owner: Optional[ServerOwner] = None
    co_owners: List[ServerOwner] = []
    player_count: Optional[int] = None
    max_players: Optional[int] = None
    join_key: Optional[str] = None
    account_requirement = None
    team_balance: Optional[bool] = None

    def _get_player(self, id: Optional[int] = None, name: Optional[str] = None):
        for _, player in self._server_cache.players.items():
            if id and player.id == id:
                return player
            if name and player.name == name:
                return player

    async def _safe_close(self):
        await self._requests._close()
        self._requests = None

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
            if error_code == error().error_code:
                raise error()

        raise APIException(error_code, "An unknown API error has occured.")

    def _handle(self, response: httpx.Response, return_type: Type[R]) -> R:
        if not response.is_success:
            self._handle_error_code(response.json().get("code"))
        return response.json()

    @_refresh_server
    @_ephemeral
    async def get_status(self):
        """Get the current server status."""
        return ServerStatus(
            self, data=self._handle(await self._requests.get("/"), Dict)
        )

    @_refresh_server
    @_ephemeral
    async def get_players(self):
        """Get all online server players."""
        return [
            ServerPlayer(self, data=p)
            for p in self._handle(await self._requests.get("/players"), List[Dict])
        ]

    @_ephemeral
    async def get_queue(self):
        """Get all players in the server join queue."""
        return [
            QueuedPlayer(self, id=p)
            for p in self._handle(await self._requests.get("/queue"), List[int])
        ]

    @_refresh_server
    @_ephemeral
    async def get_bans(self):
        """Get all server bans."""
        return [
            self._server_cache.bans.set(p.id, p)
            for p in [
                Player(self._client, data=p)
                for p in (self._handle(await self._requests.get("/bans"), Dict)).items()
            ]
        ]

    @_refresh_server
    @_ephemeral
    async def get_vehicles(self):
        """Get all spawned vehicles in the server."""
        return [
            self._server_cache.vehicles.add(Vehicle(self, data=v))
            for v in self._handle(await self._requests.get("/vehicles"), List[Dict])
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


class ServerLog(ServerModule):
    """Interact with PRC ER:LC server logs APIs."""

    def __init__(self, server: Server):
        super().__init__(server)

    @_refresh_server
    @_ephemeral
    async def get_joins(self):
        """Get server join logs."""
        [
            JoinEntry(self._server, data=e)
            for e in self._handle(await self._requests.get("/joinlogs"), List[Dict])
        ]
        return self._server_cache.join_logs.items()

    @_refresh_server
    @_ephemeral
    async def get_kills(self):
        """Get server kill logs."""
        [
            KillEntry(self._server, data=e)
            for e in self._handle(await self._requests.get("/killlogs"), List[Dict])
        ]
        return self._server_cache.kill_logs.items()

    @_refresh_server
    @_ephemeral
    async def get_commands(self):
        """Get server command logs."""
        [
            CommandEntry(self._server, data=e)
            for e in self._handle(await self._requests.get("/commandlogs"), List[Dict])
        ]
        return self._server_cache.command_logs.items()

    @_refresh_server
    @_ephemeral
    async def get_mod_calls(self):
        """Get server mod call logs."""
        [
            ModCallEntry(self._server, data=e)
            for e in self._handle(await self._requests.get("/modcalls"), List[Dict])
        ]
        return self._server_cache.mod_call_logs.items()
