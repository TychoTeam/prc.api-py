from typing import Dict, Optional, TypedDict, List, Literal, Union

PUBLIC_KEY = "MCowBQYDK2VwAyEAjSICb9pp0kHizGQtdG8ySWsDChfGqi+gyFCttigBNOA="

EventName = Literal[
    "WebhookProbe", "CustomCommand", "EmergencyCallStarted", "EmergencyCallEnded"
]
CallTeam = Literal["Police", "Fire", "DOT", "ALL"]


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
    team: CallTeam
    position: List[int]
    positionDescriptor: Optional[str]
    startedAt: int


class EmergencyCallStartedWebhookEvent(BaseWebhookEvent):
    event: Literal["EmergencyCallStarted"]
    data: EmergencyCallEventData


class EmergencyCallEndedWebhookEvent(BaseWebhookEvent):
    event: Literal["EmergencyCallEnded"]
    data: EmergencyCallEventData


WebhookEvent = Union[
    ProbeWebhookEvent,
    CustomCommandWebhookEvent,
    EmergencyCallStartedWebhookEvent,
    EmergencyCallEndedWebhookEvent,
]


class EventWebhookPayload(TypedDict):
    server: str
    events: List[WebhookEvent]
