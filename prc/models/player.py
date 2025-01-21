from typing import Tuple, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from prc.client import PRC


class Player:
    """Represents a base player."""

    def __init__(self, client: "PRC", data: Union[str, Tuple[str, str]]):
        self._client = client

        if isinstance(data, str):
            if "remote server" in data.lower():
                id, name = ("0", "Remote Server")
            else:
                name, id = data.split(":")
        else:
            id, name = [*data]

        if not id.isdigit():
            raise ValueError(f"Malformed player ID received: {data}")

        self.id: int = int(id)
        self.name: str = str(name)

        client._global_cache.players.set(self.id, self)

    def is_remote(self):
        return self.id == 0
