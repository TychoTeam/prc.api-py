"""

The main prc.api client.

"""

from .utility import KeylessCache, Cache, CacheConfig, Requests
from typing import Optional, TYPE_CHECKING, Dict, Literal
from .utility.requests import CleanAsyncClient
from .exceptions import PRCException
from .webhooks import Webhooks
from datetime import datetime
from .server import Server
import re

if TYPE_CHECKING:
    from prc import Player


class GlobalCache:
    """
    Global object caches and config. TTL in seconds, 0 to disable. (max_size, TTL)
    """

    def __init__(
        self,
        servers: CacheConfig = (3, 0),
        join_codes: CacheConfig = (3, 0),
        players: CacheConfig = (100, 0),
        invalid_keys: CacheConfig = (25, 0),
    ):
        self.servers = Cache[str, Server](*servers)
        self.join_codes = Cache[str, str](*join_codes)
        self.players = Cache[int, "Player"](*players)
        self.invalid_keys = KeylessCache[str](*invalid_keys)


class PRC:
    """
    The main PRC API client. Controls servers and global cache.

    Parameters
    ----------
    global_key
        The global authentication key (large scale apps), if any.
    default_server_key
        The default unique server key to use. This will allow you to use `get_server` without needing to pass a key.
    """

    def __init__(
        self,
        global_key: Optional[str] = None,
        default_server_key: Optional[str] = None,
        _base_url: str = "https://api.policeroleplay.community/v1",
        _cache: Optional[GlobalCache] = None,
    ):
        self._global_key = global_key
        if default_server_key:
            self._validate_server_key(default_server_key)
        self._default_server_key = default_server_key
        self._base_url = _base_url
        self._global_cache = _cache if _cache is not None else GlobalCache()
        self._session = CleanAsyncClient()
        self._key_requests = (
            Requests[Literal["/reset"]](
                base_url=self._base_url + "/api-key",
                headers={"Authorization": self._global_key},
                session=self._session,
                invalid_keys=self._global_cache.invalid_keys,
            )
            if self._global_key is not None
            else None
        )

        self.webhooks = Webhooks(self)

    def get_server(
        self, server_key: Optional[str] = None, *, ignore_global_key: bool = False
    ) -> Server:
        """
        Get a server handler using a key. Servers are cached and data is synced across the client.

        Parameters
        ----------
        server_key
            The unique server key used to authenticate requests. Defaults to `default_server_key`, if any.
        ignore_global_key
            Whether to ignore the client's global authentication key (if set). By default, it is not ignored. This may reset the cached server if the cached `ignore_global_key` is conflicting.
        """

        if not server_key:
            server_key = self._default_server_key

        if not server_key:
            raise ValueError("No [default] server-key provided but is required")

        self._validate_server_key(server_key)
        server_id = self._get_server_id(server_key)

        existing_server = self._global_cache.servers.get(server_id)
        if existing_server and existing_server._ignore_global_key == ignore_global_key:
            if (
                existing_server._global_key != self._global_key
                or existing_server._server_key != server_key
            ):
                existing_server._global_key = self._global_key
                existing_server._server_key = server_key
                existing_server._refresh_requests()

                return self._global_cache.servers.set(server_id, existing_server)
            else:
                return existing_server
        else:
            return self._global_cache.servers.set(
                server_id,
                Server(
                    client=self,
                    server_key=server_key,
                    ignore_global_key=ignore_global_key,
                ),
            )

    async def reset_key(self) -> None:
        """
        Reset the global key and generate a new one. The new key will be used automatically and will **NOT** be returned. This will reset all cache.
        """

        if not self._key_requests or self._global_key is None:
            raise ValueError("No global key is set but is required")

        response = await self._key_requests.post("/reset")

        if response.is_success:
            new_key: str = response.json()["new"]

            self._global_cache.servers.clear()
            self._global_cache.players.clear()

            self._global_key = new_key
        elif response.status_code == 403:
            self._global_cache.invalid_keys.add(self._global_key)
            raise PRCException(
                f"The global key provided is invalid and cannot be reset."
            )
        else:
            raise PRCException(
                f"An unknown error has occured while resetting the global key. ({response.status_code})"
            )

    def _get_player(self, id: Optional[int] = None, name: Optional[str] = None):
        for _, player in self._global_cache.players.items():
            if id and player.id == id:
                return player
            if name and player.name == name:
                return player

    def _validate_server_key(self, server_key: str):
        expression = r"^[a-z]{10,}\-[a-z]{40,}$"
        if not re.match(expression, server_key, re.IGNORECASE):
            raise ValueError(f"Invalid server-key format: {server_key}")

    def _get_server_id(self, server_key: str):
        parsed_key = server_key.split("-")
        return parsed_key[1]
