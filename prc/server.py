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
    overload,
)

from .utility import KeylessCache, Cache, CacheConfig, Requests, InsensitiveEnum
from .models import PlayerList, ServerPlayerList, QueuedPlayerList, VehicleList
from functools import wraps
from .exceptions import *
from .models import *
import hashlib
import asyncio
import httpx
import copy
import json

from .api_types.v1 import v1_ServerBanResponse
from .api_types.v2 import *
from .api_types.v2 import _APIMap

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
        force_fetch = kwargs.pop("fetch", False)
        try:
            args_repr = json.dumps(args, sort_keys=True, default=str)
            kwargs_repr = json.dumps(kwargs, sort_keys=True, default=str)
        except (TypeError, ValueError):
            args_repr = str(args)
            kwargs_repr = str(kwargs)

        hashed_args = hashlib.sha256(f"{args_repr}|{kwargs_repr}".encode()).hexdigest()
        cache_key = f"{func.__name__}_cache_{hashed_args}"

        if not force_fetch:
            if hasattr(self, cache_key):
                cached_result, timestamp = getattr(self, cache_key)
                if (asyncio.get_event_loop().time() - timestamp) < self._ephemeral_ttl:
                    return copy.copy(cached_result)

        result = await func(self, *args, **kwargs)

        setattr(self, cache_key, (result, asyncio.get_event_loop().time()))
        return copy.copy(result)

    return wrapper


class ServerQuery(ServerStatus):
    """
    Represents a server information query result.

    Parameters
    ----------
    server
        The server handler.
    oldest_first
        Whether to sort logs by oldest first. By default, newer logs come first.
    data
        The response data.
    """

    players: Optional[ServerPlayerList] = None
    staff: Optional[ServerStaff] = None
    queue: Optional[QueuedPlayerList] = None
    access_logs: Optional[List[AccessEntry]] = None
    kill_logs: Optional[List[KillEntry]] = None
    command_logs: Optional[List[CommandEntry]] = None
    mod_calls: Optional[List[ModCallEntry]] = None
    emergency_calls: Optional[List[EmergencyCallEntry]] = None
    vehicles: Optional[VehicleList] = None

    def __init__(
        self,
        server: "Server",
        oldest_first: bool,
        data: v2_FullServerInformation,
    ):
        super().__init__(server, data)

        if ((_players := data.get("Players"))) is not None:
            server._server_cache.players.clear()
            players = ServerPlayerList(ServerPlayer(server, data=p) for p in _players)
            server.staff_count = len([p for p in players if p.is_staff()])
            self.players = players

        if ((staff := data.get("Staff"))) is not None:
            self.staff = ServerStaff(server, data=staff)

        if ((_queue := data.get("Queue"))) is not None:
            queue = QueuedPlayerList(
                QueuedPlayer(server, id=p, index=i) for i, p in enumerate(_queue)
            )
            server.queue_count = len(queue)
            self.queue = queue

        if ((access_logs := data.get("JoinLogs"))) is not None:
            for e in access_logs:
                AccessEntry(server, data=e)
            self.access_logs = server.logs._sort(
                server._server_cache.access_logs.items(), oldest_first
            )

        if ((kill_logs := data.get("KillLogs"))) is not None:
            self.kill_logs = server.logs._sort(
                [KillEntry(server, data=e) for e in kill_logs],
                oldest_first,
            )

        if ((command_logs := data.get("CommandLogs"))) is not None:
            self.command_logs = server.logs._sort(
                [CommandEntry(server, data=e) for e in command_logs],
                oldest_first,
            )

        if ((mod_calls := data.get("ModCalls"))) is not None:
            self.mod_calls = server.logs._sort(
                [ModCallEntry(server, data=e) for e in mod_calls],
                oldest_first,
            )

        if ((emergency_calls := data.get("EmergencyCalls"))) is not None:
            self.emergency_calls = server.logs._sort(
                [EmergencyCallEntry(server, data=e) for e in emergency_calls],
                oldest_first,
            )

        if ((vehicles := data.get("Vehicles"))) is not None:
            server._server_cache.vehicles.clear()
            self.vehicles = VehicleList(Vehicle(server, data=v) for v in vehicles)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}, owner={self.owner.id}, join_code={self.join_code}>"


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
        How long, in seconds, ephemeral results (i.e, cached responses) are kept before expiring. Defaults to `3` seconds.
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
        self._requests = requests or self._refresh_requests()

        self.logs = ServerLogs(self)
        self.commands = ServerCommands(self)

    name: Optional[str] = None
    owner: Optional[ServerOwner] = None
    co_owners: List[ServerOwner] = []
    admins: List[StaffMember] = []
    mods: List[StaffMember] = []
    helpers: List[StaffMember] = []
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
        Web URL that allows users to join the game and queue automatically for the private server. Hosted by PRC. Server status must be fetched separately.

        ⚠️ *May not function properly on mobile devices.*
        """

        return (
            ("https://policeroleplay.community/join/" + self.join_code)
            if self.join_code
            else None
        )

    def is_online(self) -> Optional[bool]:
        """
        Whether the server is online (i.e, has any online players). Server status or players must be fetched separately.
        """

        return self.player_count > 0 if self.player_count else None

    def is_full(self, *, include_reserved: bool = False) -> Optional[bool]:
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
            base_url=self._client._base_url,
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

    def _raise_error_code(self, content: Any, response: httpx.Response) -> NoReturn:
        if not isinstance(content, Dict):
            raise HTTPException(
                f"Malformed response content was received: '{type(content).__name__ if content else 'None'}'",
                response,
            )

        error_code = content.get("code")
        if error_code is None:
            raise HTTPException(
                f"An API error has occurred but no code was received.",
                response,
            )

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
                        content.get("bucket"), content.get("retry_after")
                    )

                if isinstance(exception, (CommunicationError, ServerOffline)):
                    exception = _exception(command_id=content.get("commandId"))

                exception.response = response
                raise exception

        raise APIException(
            error_code,
            f"An unknown API error has occured: {content.get('message') or '...'}",
            response,
        )

    def _handle(self, response: httpx.Response, return_type: Type[R]) -> R:
        content_type: Optional[str] = response.headers.get("Content-Type", None)
        if not content_type or not content_type.startswith("application/json"):
            raise PRCException(f"Received a non-json content type: '{content_type}'")

        if not response.is_success:
            self._raise_error_code(response.json(), response)
        return response.json()

    @_refresh_server
    @_ephemeral
    async def get_info(
        self,
        *,
        all: Optional[bool] = None,
        players: bool = False,
        staff: bool = False,
        queue: bool = False,
        access_logs: bool = False,
        kill_logs: bool = False,
        command_logs: bool = False,
        mod_calls: bool = False,
        emergency_calls: bool = False,
        vehicles: bool = False,
        oldest_first: bool = False,
        **kwargs,
    ) -> ServerQuery:
        """
        Get information about the server. By default, only the server status is queried. When an option is not queried (i.e, is `False`), its property in the returned `ServerQuery` will be of type `None`.

        Parameters
        ----------
        all
            Whether to query all server information. Overrides all other kwargs.
        players
            Whether to query server players.
        staff
            Whether to query server staff.
        queue
            Whether to query the server join queue.
        access_logs
            Whether to query server access (join/leave) logs.
        kill_logs
            Whether to query server kill logs.
        command_logs
            Whether to query server command usage logs.
        mod_calls
            Whether to query server mod calls.
        emergency_calls
            Whether to query server emergency calls.
        vehicles
            Whether to query server vehicles.
        oldest_first
            Whether to sort logs by oldest first. By default, newer logs come first.
        """

        params = {
            "Players": players,
            "Staff": staff,
            "JoinLogs": access_logs,
            "Queue": queue,
            "KillLogs": kill_logs,
            "CommandLogs": command_logs,
            "ModCalls": mod_calls,
            "EmergencyCalls": emergency_calls,
            "Vehicles": vehicles,
        }

        for k, v in params.copy().items():
            if all is not None:
                params[k] = all
            elif v is False:
                params.pop(k)

        return ServerQuery(
            self,
            oldest_first,
            data=self._handle(
                await self._requests.get("/v2/server", params=params),
                v2_FullServerInformation,
            ),
        )

    @_refresh_server
    @_ephemeral
    async def get_status(self, **kwargs) -> ServerStatus:
        """
        Get the current server status.
        """

        return ServerStatus(
            self,
            data=self._handle(
                await self._requests.get("/v2/server"), v2_ServerInformation
            ),
        )

    @_refresh_server
    @_ephemeral
    async def get_players(self, **kwargs) -> ServerPlayerList:
        """
        Get all online server players.
        """

        if ((players := (await self.get_info(players=True)).players)) is not None:
            return players
        raise ValueError("Player list unexpectedly not defined")

    @overload
    async def get_player(
        self, *, id: int, name: None = ..., **kwargs
    ) -> Optional[ServerPlayer]: ...

    @overload
    async def get_player(
        self, *, id: None = ..., name: str, **kwargs
    ) -> Optional[ServerPlayer]: ...

    @_refresh_server
    async def get_player(
        self, *, id: Optional[int] = None, name: Optional[str] = None, **kwargs
    ) -> Optional[ServerPlayer]:
        """
        Get an online server player using their player ID or username, if found.

        This is equivalent to `get_players.find_player`.
        """

        players = await self.get_players(fetch=kwargs.pop("fetch", False))

        if id is not None:
            return players.find_player(id=id)
        if name is not None:
            return players.find_player(name=name)

    @_refresh_server
    @_ephemeral
    async def get_queue(self, **kwargs) -> QueuedPlayerList:
        """
        Get all players in the server join queue.
        """

        if ((queue := (await self.get_info(queue=True)).queue)) is not None:
            return queue
        raise ValueError("Queue list unexpectedly not defined")

    @_refresh_server
    @_ephemeral
    async def get_bans(self, **kwargs) -> PlayerList:
        """
        Get all banned players.
        """

        return PlayerList(
            Player(self._client, data=p, _skip_cache=True)
            for p in self._parse_api_map(
                self._handle(
                    await self._requests.get("/v1/server/bans"), v1_ServerBanResponse
                )
            ).items()
        )

    @_refresh_server
    @_ephemeral
    async def get_vehicles(self, **kwargs) -> VehicleList:
        """
        Get all spawned vehicles in the server. A single server player may have up to 2 spawned vehicles (1 primary + 1 secondary).
        """

        if ((vehicles := (await self.get_info(vehicles=True)).vehicles)) is not None:
            return vehicles
        raise ValueError("Vehicles list unexpectedly not defined")

    @_refresh_server
    @_ephemeral
    async def get_staff(self, **kwargs) -> ServerStaff:
        """
        Get all server staff members excluding server owner.
        """

        if ((staff := (await self.get_info(staff=True)).staff)) is not None:
            return staff
        raise ValueError("Staff list unexpectedly not defined")


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
        self._get_info = server.get_info


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
    async def get_access(
        self, *, oldest_first: bool = False, **kwargs
    ) -> List[AccessEntry]:
        """
        Get server access (join/leave) logs.

        Parameters
        ----------
        oldest_first
            Whether to return older logs first. By default, newer logs come first.
        """

        if (
            logs := (
                await self._get_info(access_logs=True, oldest_first=oldest_first)
            ).access_logs
        ) is not None:
            return logs
        raise ValueError("Access logs unexpectedly not defined")

    @_refresh_server
    @_ephemeral
    async def get_kills(
        self, *, oldest_first: bool = False, **kwargs
    ) -> List[KillEntry]:
        """
        Get server kill logs.

        Parameters
        ----------
        oldest_first
            Whether to return older logs first. By default, newer logs come first.
        """

        if (
            logs := (
                await self._get_info(kill_logs=True, oldest_first=oldest_first)
            ).kill_logs
        ) is not None:
            return logs
        raise ValueError("Kill logs unexpectedly not defined")

    @_refresh_server
    @_ephemeral
    async def get_commands(
        self, *, oldest_first: bool = False, **kwargs
    ) -> List[CommandEntry]:
        """
        Get server command usage logs.

        Parameters
        ----------
        oldest_first
            Whether to return older logs first. By default, newer logs come first.
        """

        if (
            logs := (
                await self._get_info(command_logs=True, oldest_first=oldest_first)
            ).command_logs
        ) is not None:
            return logs
        raise ValueError("Command logs unexpectedly not defined")

    @_refresh_server
    @_ephemeral
    async def get_mod_calls(
        self, *, oldest_first: bool = False, **kwargs
    ) -> List[ModCallEntry]:
        """
        Get server mod call logs.

        Parameters
        ----------
        oldest_first
            Whether to return older logs first. By default, newer logs come first.
        """

        if (
            logs := (
                await self._get_info(mod_calls=True, oldest_first=oldest_first)
            ).mod_calls
        ) is not None:
            return logs
        raise ValueError("Mod call list unexpectedly not defined")

    @_refresh_server
    @_ephemeral
    async def get_emergency_calls(
        self, *, oldest_first: bool = False, **kwargs
    ) -> List[EmergencyCallEntry]:
        """
        Get server emergency call logs. Call numbers are NOT unique and may be shared across teams (e.g. major server calls).

        Parameters
        ----------
        oldest_first
            Whether to return older logs first. By default, newer logs come first.
        """

        if (
            logs := (
                await self._get_info(emergency_calls=True, oldest_first=oldest_first)
            ).emergency_calls
        ) is not None:
            return logs
        raise ValueError("Emergency call list unexpectedly not defined")


CommandTargetPlayerName = Union[str, Player, VehicleOwner]
CommandTargetPlayerId = Union[int, Player, QueuedPlayer, ServerOwner]
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
            await self._requests.post("/v2/server/command", json={"command": command}),
            v2_ServerCommandExecutionResponse,
        )

    async def run(
        self,
        name: CommandName,
        *,
        targets: Optional[
            Union[Sequence[CommandTargetPlayerNameOrId], CommandTargetPlayerNameOrId]
        ] = None,
        args: Optional[Sequence[Union[CommandArg, CommandTargetPlayerNameOrId]]] = None,
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
            Specific command arguments (e.g. weather, fire event type).
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

        def parse_arg(arg: Union[CommandArg, CommandTargetPlayerNameOrId]):
            if isinstance(arg, Player):
                if _prefer_player_id:
                    return str(arg.id)
                return str(arg.name)
            if isinstance(arg, (QueuedPlayer, ServerOwner)):
                return str(arg.id)
            if isinstance(arg, VehicleOwner):
                return str(arg.name)
            if isinstance(arg, InsensitiveEnum):
                return arg.value
            return str(arg)

        if targets:
            if isinstance(targets, (str, int)):
                command += str(targets) + " "
            elif isinstance(targets, Player):
                command += Player.name + " "
            elif isinstance(targets, (QueuedPlayer, ServerOwner)):
                command += str(Player.id) + " "
            elif isinstance(targets, VehicleOwner):
                command += str(Player.name) + " "
            else:
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

    async def kill(
        self, targets: Union[Sequence[CommandTargetPlayerName], CommandTargetPlayerName]
    ):
        """
        Kill players in the server.

        Parameters
        ----------
        targets
            The player(s) to kill. A player can be a username, partial username or a player (and any of its subclasses).
        """

        await self.run("kill", targets=targets)

    async def heal(
        self, targets: Union[Sequence[CommandTargetPlayerName], CommandTargetPlayerName]
    ):
        """
        Heal players in the server.

        Parameters
        ----------
        targets
            The player(s) to heal. A player can be a username, partial username or a player (and any of its subclasses).
        """

        await self.run("heal", targets=targets)

    async def make_wanted(
        self, targets: Union[Sequence[CommandTargetPlayerName], CommandTargetPlayerName]
    ):
        """
        Make players wanted in the server.

        Parameters
        ----------
        targets
            The player(s) to make wanted. A player can be a username, partial username or a player (and any of its subclasses).
        """

        await self.run("wanted", targets=targets)

    async def remove_wanted(
        self, targets: Union[Sequence[CommandTargetPlayerName], CommandTargetPlayerName]
    ):
        """
        Remove wanted status from players in the server.

        Parameters
        ----------
        targets
            The player(s) to remove wanted status from. A player can be a username, partial username or a player (and any of its subclasses).
        """

        await self.run("unwanted", targets=targets)

    async def make_jailed(
        self, targets: Union[Sequence[CommandTargetPlayerName], CommandTargetPlayerName]
    ):
        """
        Make players jailed in the server. Teleports them to a prison cell and changes the server player's team.

        Parameters
        ----------
        targets
            The player(s) to make jailed. A player can be a username, partial username or a player (and any of its subclasses).
        """

        await self.run("jail", targets=targets)

    async def remove_jailed(
        self, targets: Union[Sequence[CommandTargetPlayerName], CommandTargetPlayerName]
    ):
        """
        Remove jailed status from players in the server.

        Parameters
        ----------
        targets
            The player(s) to remove jail status from. A player can be a username, partial username or a player (and any of its subclasses).
        """

        await self.run("unjail", targets=targets)

    async def refresh(
        self, targets: Union[Sequence[CommandTargetPlayerName], CommandTargetPlayerName]
    ):
        """
        Respawn players in the server and return them to their last positions.

        Parameters
        ----------
        targets
            The player(s) to refresh. A player can be a username, partial username or a player (and any of its subclasses).
        """

        await self.run("refresh", targets=targets)

    async def respawn(
        self, targets: Union[Sequence[CommandTargetPlayerName], CommandTargetPlayerName]
    ):
        """
        Respawn players in the server and return them to their set spawn location.

        Parameters
        ----------
        targets
            The player(s) to respawn. A player can be a username, partial username or a player (and any of its subclasses).
        """

        await self.run("load", targets=targets)

    async def teleport(
        self,
        targets: Union[Sequence[CommandTargetPlayerName], CommandTargetPlayerName],
        *,
        to: CommandTargetPlayerName,
    ):
        """
        Teleport players to another player in the server.

        Parameters
        ----------
        targets
            The player(s) to teleport. A player can be a username, partial username or a player (and any of its subclasses).
        to
            The player to be teleported to. A player can be a username, partial username or a player (and any of its subclasses).
        """

        await self.run("tp", targets=targets, args=[to])

    async def kick(
        self,
        targets: Union[Sequence[CommandTargetPlayerName], CommandTargetPlayerName],
        *,
        reason: Optional[str] = None,
    ):
        """
        Kick players from the server.

        Parameters
        ----------
        targets
            The player(s) to kick. A player can be a username, partial username or a player (and any of its subclasses).
        reason
            The reason for the kick, if any.
        """

        await self.run("kick", targets=targets, text=reason)

    async def ban(
        self,
        targets: Union[
            Sequence[CommandTargetPlayerNameOrId], CommandTargetPlayerNameOrId
        ],
    ):
        """
        Ban players from the server.

        Parameters
        ----------
        targets
            The player(s) to ban. A player can be a username, partial username, ID or a player (and any of its subclasses).
        """

        await self.run("ban", targets=targets, _prefer_player_id=True)

    async def unban(
        self,
        targets: Union[
            Sequence[CommandTargetPlayerNameOrId], CommandTargetPlayerNameOrId
        ],
    ):
        """
        Unban players from the server.

        Parameters
        ----------
        targets
            The player(s) to unban. A player can be a username, ID or a player (and any of its subclasses).
        """

        await self.run("unban", targets=targets, _prefer_player_id=True)

    async def shutdown(self):
        """
        Shutdown the server. Kicks all players in-game, including players with elevated permissions.
        """

        await self.run("shutdown")

    async def grant_helper(
        self,
        targets: Union[
            Sequence[CommandTargetPlayerNameOrId], CommandTargetPlayerNameOrId
        ],
    ):
        """
        Grant helper permissions to players in the server.

        Parameters
        ----------
        targets
            The player(s) to grant permissions to. A player can be a username, partial username, ID or a player (and any of its subclasses).
        """

        await self.run("helper", targets=targets, _prefer_player_id=True)

    async def revoke_helper(
        self,
        targets: Union[
            Sequence[CommandTargetPlayerNameOrId], CommandTargetPlayerNameOrId
        ],
    ):
        """
        Revoke helper permissions to players in the server.

        Parameters
        ----------
        targets
            The player(s) to revoke permissions from. A player can be a username, partial username, ID or a player (and any of its subclasses).
        """

        await self.run("unhelper", targets=targets, _prefer_player_id=True)

    async def grant_mod(
        self,
        targets: Union[
            Sequence[CommandTargetPlayerNameOrId], CommandTargetPlayerNameOrId
        ],
    ):
        """
        Grant moderator permissions to players in the server.

        Parameters
        ----------
        targets
            The player(s) to grant permissions to. A player can be a username, partial username, ID or a player (and any of its subclasses).
        """

        await self.run("mod", targets=targets, _prefer_player_id=True)

    async def revoke_mod(
        self,
        targets: Union[
            Sequence[CommandTargetPlayerNameOrId], CommandTargetPlayerNameOrId
        ],
    ):
        """
        Revoke moderator permissions from players in the server.

        Parameters
        ----------
        targets
            The player(s) to revoke permissions from. A player can be a username, partial username, ID or a player (and any of its subclasses).
        """

        await self.run("unmod", targets=targets, _prefer_player_id=True)

    async def grant_admin(
        self,
        targets: Union[
            Sequence[CommandTargetPlayerNameOrId], CommandTargetPlayerNameOrId
        ],
    ):
        """
        Grant admin permissions to players in the server.

        Parameters
        ----------
        targets
            The player(s) to grant permissions to. A player can be a username, partial username, ID or a player (and any of its subclasses).
        """

        await self.run("admin", targets=targets, _prefer_player_id=True)

    async def revoke_admin(
        self,
        targets: Union[
            Sequence[CommandTargetPlayerNameOrId], CommandTargetPlayerNameOrId
        ],
    ):
        """
        Revoke admin permissions from players in the server.

        Parameters
        ----------
        targets
            The player(s) to revoke permissions from. A player can be a username, partial username, ID or a player (and any of its subclasses).
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

    async def send_pm(
        self,
        targets: Union[Sequence[CommandTargetPlayerName], CommandTargetPlayerName],
        text: str,
    ):
        """
        Send a private message to players in the server (dismissable popup).

        Parameters
        ----------
        targets
            The player(s) to message. A player can be a username, partial username or a player (and any of its subclasses).
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
        Start a fire event at a random location in the server.

        Parameters
        ----------
        type
            The type of fire event to start.
        """

        await self.run("startfire", args=[type])

    async def stop_fires(self, *, dumpster: bool = False):
        """
        Stop all active fire events in the server.

        Parameters
        ----------
        dumpster
            Whether to stop dumpster fires only. Otherwise, **only non-dumpster fires** will be stopped.
        """

        if dumpster:
            await self.run("stopdumpsterfire")
        else:
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
