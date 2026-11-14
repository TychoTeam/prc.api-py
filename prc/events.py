from typing import TYPE_CHECKING, Any, Optional
from .models import *


if TYPE_CHECKING:
    from .client import PRC


class Events:
    """
    The main class to interface with the PRC ER:LC HTTP [webhook event](https://apidocs.erlc.gg/event-webhooks) parsers.

    Parameters
    ----------
    client
        The global/shared PRC client.
    """

    def __init__(self, client: "PRC"):
        self._client = client

    def parse(self, /, event_payload: Any) -> EventMessage:
        """
        Parse an event message payload.

        Parameters
        ----------
        event_payload
            The event JSON payload. Must be a valid `EventWebhookPayload`.
        """

        return EventMessage(self, event_payload)

    def safe_parse(self, /, event_payload: Any) -> Optional[EventMessage]:
        """
        Safely parse an event message payload.

        Parameters
        ----------
        event_payload
            The event JSON payload. Must be a valid `EventWebhookPayload`.
        """

        try:
            return EventMessage(self, event_payload)
        # It is bad practice to catch all Exceptions, should be improved.
        except Exception:
            return None

    def parse_event(self, /, event_data: Any) -> AnyEvent:
        """
        Parse a single event payload.

        Parameters
        ----------
        event_data
            The event JSON data.
        """

        if not isinstance(event_data["event"], str):
            raise ValueError(f"Event type not set or is invalid.")

        if event_data["event"] == EventType.PROBE:
            return ProbeEvent(event_data)

        if event_data["event"] == EventType.CUSTOM_COMMAND:
            return CustomCommandEvent(self._client, event_data)

        if event_data["event"] == EventType.CALL_STARTED:
            return CallStartEvent(self._client, event_data)

        if event_data["event"] == EventType.CALL_ENDED:
            return CallStartEvent(self._client, event_data)

        raise ValueError(f"Unknown event type: '{event_data['event']}'")

    def safe_parse_event(self, /, event_data: Any) -> Optional[AnyEvent]:
        """
        Safely parse a single event payload.

        Parameters
        ----------
        event_data
            The event JSON data.
        """

        try:
            return self.parse_event(event_data)
        # Refer to note in .safe_parse().
        except Exception:
            return None
