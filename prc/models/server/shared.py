from prc.utility import DisplayNameEnum
from typing import Tuple
import math


class Location:
    """
    Represents a location with (x, z) coordinates in a server.

    Parameters
    ----------
    x
        The location's X coordinate.
    z
        The location's Z coordinate.
    """

    x: float
    z: float

    def __init__(self, x: float, z: float):
        self.x = float(x)
        self.z = float(z)

    @property
    def coordinates(self) -> Tuple[float, float]:
        """
        A tuple representing location coordinates (x, z) on an official [PRC API map](https://api.erlc.gg/maps/).
        """

        return (self.x, self.z)

    def distance_from(self, x: float, z: float, *, round_to: int = 3) -> float:
        """
        Find the distance between this location and an (x, z) coordinate. Alternatively, use `Location1 - Location2` (i.e, subtraction) to find the distance between 2 locations.
        """

        return round(math.hypot(self.x - x, self.z - z), round_to)

    def __sub__(self, other: "Location") -> float:
        return self.distance_from(other.x, other.z)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Location)
            and (round(self.x, 1) == round(other.x, 1))
            and (round(self.z, 1) == round(other.z, 1))
        )

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} coordinates={self.coordinates}>"


class ServerTeam(DisplayNameEnum):
    """
    Enum that represents a server team.
    """

    CIVILIAN = (0, "Civilian")
    SHERIFF = (1, "Sheriff")
    POLICE = (2, "Police")
    FIRE = (3, "Fire")
    DOT = (4, "DOT")
    JAIL = (5, "Jail")
