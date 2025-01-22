"""

The main prc.api client

"""

from .server import Server
from .utility import Cache, CacheConfig
from .utility.requests import CleanAsyncClient
from typing import Optional, TYPE_CHECKING
import re

if TYPE_CHECKING:
    from prc import Player


class GlobalCache:
    """Global object caches and config. TTL in seconds, 0 to disable. (max_size, TTL)"""

    def __init__(
        self,
        servers: CacheConfig = (2, 0),
        players: CacheConfig = (100, 0),
    ):
        self.servers = Cache[str, Server](*servers)
        self.players = Cache[int, "Player"](*players)


class PRC:
    """The main PRC API client. Controls servers and global cache."""

    def __init__(
        self,
        global_key: Optional[str] = None,
        default_server_key: Optional[str] = None,
        base_url: str = "https://api.policeroleplay.community/v1",
        cache=GlobalCache(),
    ):
        self._global_key = global_key
        if default_server_key:
            self._validate_server_key(default_server_key)
        self._default_server_key = default_server_key
        self._base_url = base_url
        self._global_cache = cache
        self._session = CleanAsyncClient()

    def get_server(
        self, server_key: Optional[str] = None, ignore_global_key: bool = False
    ):
        """Get a server handler using a key. Defaults to `default_server_key` if no `server_key` is passed. Servers are cached and data is synced across the client. Setting `ignore_global_key` may reset the cached server if cached `ignore_global_key` is conflicting."""
        if not server_key:
            server_key = self._default_server_key

        if not server_key:
            raise ValueError("No [default] server-key provided but is required")

        self._validate_server_key(server_key)
        server_id = self._get_server_id(server_key)

        existing_server = self._global_cache.servers.get(server_id)
        if existing_server and existing_server._ignore_global_key == ignore_global_key:
            return existing_server
        return self._global_cache.servers.set(
            server_id,
            Server(
                client=self, server_key=server_key, ignore_global_key=ignore_global_key
            ),
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
