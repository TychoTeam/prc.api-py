"""

The main prc.api client.

"""

from typing import Optional, TYPE_CHECKING, Union
from httpx import URL
import re

from .utility import (
    KeylessCache,
    Cache,
    CacheConfig,
    Requests,
    HeaderType,
    CacheSweeper,
)
from .utility.requests import CleanAsyncClient
from .exceptions import HTTPException
from .webhooks import Webhooks
from .server import Server

from .api_types.v1 import v1_ApiKeyResetResponse

if TYPE_CHECKING:
    from prc import Player


class GlobalCache:
    """
    Global object caches and config. TTL in seconds, 0 to disable. (max_size, TTL)
    """

    def __init__(
        self,
        sweeper: CacheSweeper,
        servers: CacheConfig = (3, 0),
        join_codes: CacheConfig = (3, 0),
        players: CacheConfig = (100, 0),
        invalid_keys: CacheConfig = (25, 0),
    ):
        self.servers = Cache[str, Server](sweeper, *servers)
        self.join_codes = Cache[str, str](sweeper, *join_codes)
        self.players = Cache[int, "Player"](sweeper, *players)
        self.invalid_keys = KeylessCache[str](sweeper, *invalid_keys)


class PRC:
    """
    The main PRC API client.

    Parameters
    ----------
    global_key
        The [global authentication key](https://apidocs.erlc.gg/large-applications) (for public & large scale apps).

        Each client is designed to work with a **single** global key for one or multiple *server* keys. It is recommended to use multiple clients for different *global* keys.
    default_server_key
        The default unique server key to use. This will allow you to use `.get_server()` and access `.default_server` without needing to pass a key.
    application_id
        The developer application ID (for public apps). [Learn More](https://apidocs.erlc.gg/creating-public-applications)
    base_url
        The base URL this client will use to send requests. Can be modified to use a proxy. **The URI scheme must be set (i.e, `http[s]`).**
    """

    def __init__(
        self,
        global_key: Optional[str] = None,
        default_server_key: Optional[str] = None,
        application_id: Optional[Union[str, int]] = None,
        base_url: str = "https://api.erlc.gg",
        _cache: Optional[GlobalCache] = None,
    ):
        self._base_url = URL(url=base_url)
        self._global_key = global_key

        self._default_server_key = None
        if default_server_key is not None:
            self._validate_server_key(server_key=default_server_key)
            self._default_server_key = default_server_key

        self.application_id = None
        if application_id is not None:
            application_id = str(application_id)
            self._validate_application_id(application_id=application_id)
            self.application_id = application_id

        self._session = CleanAsyncClient()

        self._cache_sweeper = CacheSweeper()
        self._global_cache = (
            _cache if _cache is not None else GlobalCache(sweeper=self._cache_sweeper)
        )

        self._key_requests = None
        if self._global_key:
            self._key_requests = Requests(
                base_url=self._base_url.join("v1/api-key/"),
                dynamic_headers=self._get_key_headers,
                session=self._session,
                invalid_keys=self._global_cache.invalid_keys,
                sweeper=self._cache_sweeper,
            )

        self._webhooks = Webhooks(self)

    @property
    def webhooks(self) -> Webhooks:
        """
        Handlers for private server log messages (Discord webhooks).
        """

        return self._webhooks

    @property
    def default_server(self) -> Optional[Server]:
        """
        The default server handler (only if `default_server_key` is set). To customize the server handler arguments, use `.get_server()`
        """

        if self._default_server_key is not None:
            return self.get_server(server_key=self._default_server_key)

    def get_server(
        self,
        server_key: Optional[str] = None,
        *,
        ephemeral_ttl: Optional[float] = None,
        ignore_global_key: bool = False,
    ) -> Server:
        """
        Get a server handler using a key. Servers are cached and synced across the client.

        Parameters
        ----------
        server_key
            The unique server key used to authenticate requests. Defaults to `default_server_key`, if any.
        ephemeral_ttl
            How long, in seconds, ephemeral results (i.e, cached responses) are kept before expiring. Defaults to `1` second. Set to `0` to disable.

            ⚠️ ALL existing `Server` instances with the same server ID will use the new TTL.
        ignore_global_key
            Whether to ignore the client's global authentication key (if set). By default, it is not ignored.

            ⚠️ This will apply to ALL existing `Server` instances with the same server ID.
        """

        if not server_key:
            server_key = self._default_server_key

        if not server_key:
            raise ValueError("No [default] server-key provided but is required")

        self._validate_server_key(server_key=server_key)
        server_id = self._get_server_id(server_key=server_key)

        existing_server = self._global_cache.servers.get(server_id)
        if existing_server:
            existing_server._ignore_global_key = ignore_global_key

            if ephemeral_ttl is not None:
                existing_server._ephemeral_ttl = ephemeral_ttl

            # It is possible that the server secret has rotated, hence the cached key could be out of date.
            if existing_server._server_key != server_key:
                existing_server._server_key = server_key

            return existing_server

        else:
            return self._global_cache.servers.set(
                server_id,
                Server(
                    client=self,
                    server_key=server_key,
                    ephemeral_ttl=ephemeral_ttl or 1.0,
                    ignore_global_key=ignore_global_key,
                ),
            )

    async def reset_key(self) -> str:
        """
        Reset the global key and generate a new one. The new key will be applied automatically to the client and will be returned.

        ⚠️ You **MUST** securely save the newly generated key outside the running process.

        For large scale apps: if you reset your key and the process exits without saving the key somewhere, your key will be **LOST** and you must contact PRC.
        """

        if not self._key_requests or self._global_key is None:
            raise ValueError("No global key is set but is required.")

        response = await self._key_requests.post("reset")

        if response.is_success:
            body: v1_ApiKeyResetResponse = response.json()
            new_key = body["new"]
            self._global_key = new_key

            return new_key

        elif response.status_code == 403:
            self._global_cache.invalid_keys.add(self._global_key)
            raise HTTPException(
                f"The global key provided is invalid and could not be reset.",
                response,
            )

        raise HTTPException(
            f"An unknown error has occured while resetting the global key.",
            response,
        )

    def _get_player(
        self, id: Optional[int] = None, name: Optional[str] = None
    ) -> Optional["Player"]:
        if id is not None:
            return self._global_cache.players.get(id)

        if name is not None:
            for _, player in self._global_cache.players.items():
                if player.name.lower() == name.lower():
                    return player

    def _get_key_headers(self) -> HeaderType:
        headers = {}
        if self._global_key:
            headers["Authorization"] = self._global_key

        return headers

    _id_expression = re.compile(r"^\w+$")
    _key_expression = re.compile(r"^[a-z0-9]+\-[a-z0-9]+$", re.IGNORECASE)

    @classmethod
    def _validate_application_id(cls, *, application_id: str):
        if not cls._id_expression.match(application_id):
            raise ValueError(f"Invalid application ID provided: {application_id}")

    @classmethod
    def _validate_server_key(cls, *, server_key: str):
        if not cls._key_expression.match(server_key):
            raise ValueError(f"Invalid server-key provided.")

    @classmethod
    def _get_server_id(cls, *, server_key: str) -> str:
        elements = server_key.split("-")
        if not elements[1]:
            raise ValueError(f"Invalid server-key provided.")
        return elements[1]

    @classmethod
    def _make_authorization_url(
        cls, *, application_id: Union[str, int], server_id: str
    ) -> str:
        return f"https://api.erlc.gg/server-owners/server/{server_id}/authorize/{application_id}"
