from typing import Dict, TypedDict, List, Literal, Union

PUBLIC_KEY = "MCowBQYDK2VwAyEAjSICb9pp0kHizGQtdG8ySWsDChfGqi+gyFCttigBNOA="


class BaseWebhookEvent(TypedDict):
    event: Literal["WebhookProbe", "CustomCommand", "EmergencyCall"]
    timestamp: int


class ProbeWebhookEvent(BaseWebhookEvent):
    origin: str
    data: Dict


class CustomCommandWebhookEvent(BaseWebhookEvent):
    command: str
    argument: str
    origin: str


class EmergencyCallWebhookEvent(BaseWebhookEvent):
    # waiting for this to actually work omg
    pass


WebhookEvent = Union[
    ProbeWebhookEvent, CustomCommandWebhookEvent, EmergencyCallWebhookEvent
]


class EventWebhookPayload(TypedDict):
    server: str
    events: List[WebhookEvent]
