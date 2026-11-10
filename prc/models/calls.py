from typing import TYPE_CHECKING, List, Optional, Union
from datetime import datetime
from enum import Enum

from .server.player import PartialServerPlayer
from .server.location import Location

if TYPE_CHECKING:
    from prc.server import Server
    from .events import EventPlayer


class CallTeam(str, Enum):
    """
    Enum that represents an emergency call team.
    """

    LAW_ENFORCEMENT = "Police"
    FIRE = "Fire"
    DOT = "DOT"
    ALL_TEAMS = "ALL"


class CallPlayer(PartialServerPlayer):
    """
    Represents a server partial player referenced in a call entry.

    Parameters
    ----------
    server
        The server handler.
    id
        The player ID.
    """

    id: int

    def __init__(self, server: "Server", id: int):
        self._server = server

        self.id = int(id)

        super().__init__(server, value=self.id)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}>"


class CallPlayerList(List[CallPlayer]):
    def copy(self):
        return CallPlayerList(self)

    def find_player(self, *, id: int) -> Optional[CallPlayer]:
        """
        Find a call player using their player ID.
        """

        return next((p for p in self if p.id == id), None)

    def has_player(self, *, id: int) -> bool:
        """
        Determine whether a player exists in this call player list using their player ID.
        """

        return bool(self.find_player(id=id))


class CallLocation(Location):
    """
    Represents a call's location in a server.

    Parameters
    ----------
    position
        The call location (x,y) position.
    descriptor
        The call location descriptor.
    """

    descriptor: Optional[str]

    def __init__(self, *, position: List[int], descriptor: Optional[str]):
        self.descriptor = str(descriptor) if descriptor else None

        super().__init__(x=position[0], z=position[1])

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} coordinates={self.coordinates}, descriptor={self.descriptor}>"


class EmergencyCall:
    """
    Represents an emergency call (shared class).

    Parameters
    ----------
    server
        The server handler.
    data
        The response data.

    Attributes
    ----------
    responders
        The players attached to the call.
    team
        The team the call was sent to. This may be `ALL` teams in very certain cases (e.g. major server calls received via event webhooks only).
    caller
        The player that originally made the call. Not included in automatic server calls.
    call_number
        The call number. Unqiue per team. Different calls in different teams may share the same number.
    call_description
        The call description. May not be set in some cases, mostly 911 calls.
    location
        The call location (x, z) and area descriptor (if any).
    started_at
        The time at which the call was made.
    """

    responders: Union[CallPlayerList, List["EventPlayer"]]
    team: CallTeam
    caller: Optional[Union[CallPlayer, "EventPlayer"]]
    call_number: int
    call_description: Optional[str]
    location: CallLocation
    started_at: datetime

    def is_911(self) -> bool:
        """
        Whether this emergency call is a player 911 call and not a server call.
        """

        return bool(self.caller)

    def is_automatic(self) -> bool:
        """
        Whether this emergency call is an automatic server call and not a 911 call.
        """

        return not self.is_911()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} call_number={self.call_number}, team={self.team}, caller={self.caller.id if self.caller else None}, description={self.call_description}, responders={len(self.responders)}>"
