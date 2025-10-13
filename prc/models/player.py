from typing import Tuple, Union, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from prc.client import PRC


class Player:
    """
    Represents a base player.

    Parameters
    ----------
    client
        The global/shared PRC client.
    data
        The player name and ID. Either a tuple or default response format (`PlayerName:123`).
    """

    def __init__(
        self,
        client: "PRC",
        data: Union[str, Tuple[str, str]],
        _skip_cache: Optional[bool] = False,
    ):
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

        self.id = int(id)
        self.name = str(name)

        if not self.is_remote() and not _skip_cache:
            client._global_cache.players.set(self.id, self)

    def is_remote(self) -> bool:
        """
        Whether this is the remote player (aka. virtual server management).
        """

        return self.id == 0

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Player):
            return self.id == other.id
        return False

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}, id={self.id}>"
