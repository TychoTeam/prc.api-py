from enum import Enum


class ServerTeam(str, Enum):
    """
    Enum that represents a server team.
    """

    CIVILIAN = "Civilian"
    SHERIFF = "Sheriff"
    POLICE = "Police"
    FIRE = "Fire"
    DOT = "DOT"
    JAIL = "Jail"


__all__ = ["ServerTeam"]
