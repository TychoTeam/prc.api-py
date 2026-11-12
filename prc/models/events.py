from typing import TYPE_CHECKING, List, Optional, Union
from datetime import datetime
from enum import Enum


from .calls import CallTeam, EmergencyCall, CallLocation
from .player import BasePlayer, Player

if TYPE_CHECKING:
    from prc.api_types.events import *
    from prc.events import Events
    from prc.server import Server
    from prc.client import PRC


class EventSource(Enum):
    """
    Enum that represents the source (i.e, sender) of an event message.
    """

    GLOBAL = 0
    SERVER = 1


class EventType(str, Enum):
    """
    Enum that represents an event type.
    """

    PROBE = "WebhookProbe"
    CUSTOM_COMMAND = "CustomCommand"
    CALL_STARTED = "EmergencyCallStarted"
    CALL_ENDED = "EmergencyCallEnded"


class EventPlayer(BasePlayer):
    """
    Represents a player referenced in an event.

    Parameters
    ----------
    client
        The global/shared PRC client.
    player_id
        The player ID.

    Attributes
    ----------
    id
        The player ID.
    """

    id: int

    def __init__(self, client: "PRC", player_id: int):
        self._client = client

        self.id = int(player_id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, (EventPlayer, Player)) and self.id == other.id

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}>"


class Event:
    """
    Base class for all [event webhook](https://apidocs.erlc.gg/event-webhooks) message events.

    Parameters
    ----------
    event_data
        The event data.

    Attributes
    ----------
    event_type
        The webhook event type.
    event_created_at
        The time at which the event was created.
    """

    event_type: EventType
    event_created_at: datetime

    def __init__(self, event_data: "WebhookEvent"):
        if event_data["event"] != self.event_type:
            raise ValueError(f"Expected event type to be {self.event_type.value}")

        self.event_created_at = datetime.fromtimestamp(event_data["timestamp"])

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} created_at={self.event_created_at}>"


class ProbeEvent(Event):
    """
    Represents a webhook probe event.

    Parameters
    ----------
    event_data
        The event data.
    """

    event_type = EventType.PROBE

    def __init__(self, event_data: "ProbeWebhookEvent"):
        super().__init__(event_data)


class CustomCommandEvent(Event):
    """
    Represents a webhook custom command event.

    Parameters
    ----------
    client
        The global/shared PRC client.
    event_data
        The event data.

    Attributes
    ----------
    player
        The player who ran the command.
    command
        The custom command name (e.g. `say` in `;say hi`).

        ⚠️ Commands do not support numbers and other non-alphabetical characters. They may get parsed as arguments.
    argument
        The argument sent with the command (e.g. `hi` in `;say hi`). Not all commands have arguments, it depends on player input.
    """

    event_type = EventType.CUSTOM_COMMAND
    player: EventPlayer
    command: str
    argument: Optional[str]

    def __init__(self, client: "PRC", event_data: "CustomCommandWebhookEvent"):
        super().__init__(event_data)

        self.player = EventPlayer(client, player_id=int(event_data["origin"]))
        self.command = str(event_data["data"]["command"])
        self.argument = (
            str(arg) if (arg := event_data["data"].get("argument")) else None
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} command={self.command}, player=({self.player.id}), created_at={self.event_created_at}>"


class CallEvent(EmergencyCall, Event):
    """
    Represents a webhook call-related event.

    Parameters
    ----------
    client
        The global/shared PRC client.
    event_data
        The event data.
    """

    def __init__(
        self,
        client: "PRC",
        event_data: Union[
            "EmergencyCallStartedWebhookEvent", "EmergencyCallEndedWebhookEvent"
        ],
    ):
        super().__init__(event_data)

        self.responders = [
            EventPlayer(client, player_id=player_id)
            for player_id in event_data["data"].get("players", [])
        ]
        self.caller = (
            EventPlayer(client, player_id=int(caller_id))
            if (caller_id := event_data["data"].get("caller", None))
            else None
        )
        self.call_number = int(event_data["data"]["callNumber"])
        self.call_description = (
            str(description)
            if (description := event_data["data"].get("description", None))
            else None
        )
        self.location = CallLocation(
            position=event_data["data"]["position"],
            descriptor=event_data["data"].get("positionDescriptor", None),
        )
        self.started_at = datetime.fromtimestamp(event_data["data"]["startedAt"])

        self.team = CallTeam(event_data["data"]["team"])

    def is_automatic_call(self) -> bool:
        """
        Whether this call is an automatic server call (not a 911 call).
        """

        return self.caller == None

    def is_911_call(self) -> bool:
        """
        Whether this call is player 911 call.
        """

        return self.caller != None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} call_number={self.call_number}, team={self.team}>"


class CallStartEvent(CallEvent):
    """
    Represents a webhook call start event.
    """

    event_type = EventType.CALL_STARTED

    def is_major_call(self) -> bool:
        """
        Whether this call originated from a major server call. This is specific to call start events only.
        """

        if self.team == CallTeam.ALL_TEAMS:
            return True
        return False


class CallEndEvent(CallEvent):
    """
    Represents a webhook call end event.
    """

    event_type = EventType.CALL_ENDED


AnyEvent = Union[ProbeEvent, CustomCommandEvent, CallStartEvent, CallEndEvent]


class EventMessage:
    """
    Represents an [event webhook](https://apidocs.erlc.gg/event-webhooks) full message.

    Parameters
    ----------
    events
        An initialized events handler.
    data
        The full event webhook payload.

    Attributes
    ----------
    source
        The source of the event message.
        - Global messages are occasionally sent for health and safety checks.
        - Server messages are game-initiated, either by players or automatically by a game server.
    server
        The server handler. Only set when the message source is a private server **and** the server handler is cached (i.e, the full server key has been loaded into the global client).
    server_id
        The ER:LC internal server ID the message was sent from. Only included when the message source is a private server.

        Server IDs can be used to identify the private server -only if the full server key is known- as IDs are the non-secret part of the full key. [Learn More](https://apidocs.erlc.gg/how-to-obtain-your-server-key#anatomy-of-your-server-key)
    events
        A list of all new events sent in the message. Your handling logic must accept multiple events in a single message.
    """

    source: EventSource
    server: Optional["Server"]
    server_id: Optional[str]
    events: List[AnyEvent]

    def __init__(self, events: "Events", data: "EventWebhookPayload"):
        if data["server"] == "global":
            self.source = EventSource.GLOBAL
        else:
            self.source = EventSource.SERVER
            self.server_id = str(data["server"])
            self.server = events._client._global_cache.servers.get(self.server_id)

        self.events = [events.parse_event(event) for event in data["events"]]

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} source={self.source}, events={len(self.events)}>"


__all__ = [
    "EventSource",
    "EventType",
    "EventPlayer",
    "Event",
    "ProbeEvent",
    "CustomCommandEvent",
    "CallEvent",
    "CallStartEvent",
    "CallEndEvent",
    "AnyEvent",
    "EventMessage",
]
