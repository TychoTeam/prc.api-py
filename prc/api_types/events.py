from typing import Dict, Optional, TypedDict, List, Literal, Union

PUBLIC_KEY = "MCowBQYDK2VwAyEAjSICb9pp0kHizGQtdG8ySWsDChfGqi+gyFCttigBNOA="

EventName = Literal[
    "WebhookProbe", "CustomCommand", "EmergencyCallStarted", "EmergencyCallEnded"
]
CallTeamName = Literal["Police", "Fire", "DOT", "ALL"]


# Event data


class BaseWebhookEvent(TypedDict):
    origin: str
    timestamp: int


class ProbeWebhookEvent(BaseWebhookEvent):
    event: Literal["WebhookProbe"]
    data: Dict


class CustomCommandEventData(TypedDict):
    command: str
    argument: str


class CustomCommandWebhookEvent(BaseWebhookEvent):
    event: Literal["CustomCommand"]
    data: CustomCommandEventData


class EmergencyCallEventData(TypedDict):
    players: List[int]
    caller: Optional[int]
    description: Optional[str]
    callNumber: int
    team: CallTeamName
    position: List[int]
    positionDescriptor: Optional[str]
    startedAt: int


class EmergencyCallStartedWebhookEvent(BaseWebhookEvent):
    event: Literal["EmergencyCallStarted"]
    data: EmergencyCallEventData


class EmergencyCallEndedWebhookEvent(BaseWebhookEvent):
    event: Literal["EmergencyCallEnded"]
    data: EmergencyCallEventData


# Event data union

WebhookEvent = Union[
    ProbeWebhookEvent,
    CustomCommandWebhookEvent,
    EmergencyCallStartedWebhookEvent,
    EmergencyCallEndedWebhookEvent,
]

# Payload


class EventWebhookPayload(TypedDict):
    server: str
    events: List[WebhookEvent]


__all__ = [
    "PUBLIC_KEY",
    "EventName",
    "CallTeamName",
    "BaseWebhookEvent",
    "ProbeWebhookEvent",
    "CustomCommandWebhookEvent",
    "EmergencyCallStartedWebhookEvent",
    "EmergencyCallEndedWebhookEvent",
    "WebhookEvent",
    "EventWebhookPayload",
]
