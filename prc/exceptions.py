"""

All exceptions in use by the prc.api package.

"""

# Base Exception

from typing import Optional


class PRCException(Exception):
    """Base exception, can be used to catch all package exception."""

    def __init__(self, message: str):
        super().__init__(message)


class HTTPException(PRCException):
    """Base exception to catch all HTTP response errors."""

    def __init__(self, message: str, status_code: int):
        self._message = message
        self._status_code = status_code

        super().__init__(f"[{status_code}] {message}")

    @property
    def status_code(self) -> int:
        """The HTTP response status code."""

        return self._status_code

    @status_code.setter
    def status_code(self, value: int):
        self._status_code = value

    @property
    def message(self) -> str:
        """The generic error message."""

        return self._message

    def is_server_error(self) -> bool:
        """Whether the response status is a `5XX`."""

        return self.status_code >= 500 and self.status_code <= 599

    def is_client_error(self) -> bool:
        """Whether the response status is a `4XX`."""

        return self.status_code >= 400 and self.status_code <= 499

    def __str__(self):
        return f"[{self.status_code}] {self.message}"


class APIException(HTTPException):
    """Base exception to catch known PRC API error responses."""

    def __init__(self, code: int, message: str, status_code: int = 0):
        self._code = code

        super().__init__(message, status_code)

    @property
    def code(self):
        return self._code

    def __str__(self):
        return f"[{self.status_code}] ({self.code}) {self.message}"


# Generic Exceptions


class RequestTimeout(PRCException):
    """Exception raised when a HTTP request times out."""

    def __init__(self, retry: int, max_retries: int, timeout: float):
        self.retry = retry
        self.max_retries = max_retries
        self.timeout = timeout

        super().__init__(
            f"PRC API took too long to respond. ({retry}/{max_retries} retries) ({timeout}s timeout)"
        )


class BadContentType(HTTPException):
    """Exception raised when a non-JSON content type is received."""

    def __init__(self, status_code: int, content_type: Optional[str] = None):
        self.content_type = content_type

        super().__init__(
            f"Received a non-json content type: '{content_type}'", status_code
        )


# API Exceptions


class UnknownError(APIException):
    """Exception raised when an unknown server-side error occurs."""

    def __init__(self):
        super().__init__(
            0,
            "Unknown error occurred. If this is persistent, contact PRC via an API ticket.",
        )


class CommunicationError(APIException):
    """Exception raised when an error occurs while communicating with Roblox and/or the in-game private server."""

    def __init__(self, command_id: Optional[str] = None):
        self.command_id = command_id or "unknown"

        super().__init__(
            1001,
            "An error occurred while communicating with Roblox and/or the in-game private server.",
        )


class InternalError(APIException):
    """Exception raised when an internal server-side error occurs."""

    def __init__(self):
        super().__init__(
            1002,
            "An internal server-side error occurred. If this is persistent, contact PRC via an API ticket.",
        )


class InvalidServerKey(APIException):
    """Exception raised when the server-key is invalid or was regenerated."""

    def __init__(self):
        super().__init__(2002, "You provided an invalid (or regenerated) server-key.")


class InvalidGlobalKey(APIException):
    """Exception raised when the global API key is invalid."""

    def __init__(self):
        super().__init__(2003, "You provided an invalid global API key.")


class BannedServerKey(APIException):
    """Exception raised when the server-key is banned from accessing the API."""

    def __init__(self):
        super().__init__(
            2004, "Your server-key is currently banned from accessing the API."
        )


class InvalidCommand(APIException):
    """Exception raised when an invalid command is sent."""

    def __init__(self):
        super().__init__(3001, "The command you sent is invalid.")


class ServerOffline(APIException):
    """Exception raised when the server being reached is currently offline (has no players)."""

    def __init__(self, command_id: Optional[str] = None):
        self.command_id = command_id or "unknown"

        super().__init__(
            3002,
            "The server you are attempting to reach is currently offline (has no players).",
        )


class RateLimited(APIException):
    """Exception raised when a rate limit is exceeded. The package handles automatically handles rate limits; this should only occur when other applications are using the same IP as you."""

    def __init__(
        self, bucket: Optional[str] = None, retry_after: Optional[float] = None
    ):
        self.bucket = bucket or "unknown"
        self.retry_after = retry_after or 0.0

        super().__init__(
            4001, f"You are being rate limited. Retry after {self.retry_after:.3f}s."
        )


class RestrictedCommand(APIException):
    """Exception raised when a restricted command is sent."""

    def __init__(self):
        super().__init__(4002, "The command you sent is restricted.")


class ProhibitedMessage(APIException):
    """Exception raised when a prohibited message is sent."""

    def __init__(self):
        super().__init__(4003, "The message you sent is prohibited.")


class RestrictedResource(APIException):
    """Exception raised when accessing a restricted resource."""

    def __init__(self):
        super().__init__(9998, "The resource you are accessing is restricted.")


class OutOfDateModule(APIException):
    """Exception raised when the module running in the in-game private server is out of date."""

    def __init__(self):
        super().__init__(
            9999,
            "The module running in the in-game private server is out of date, please restart the server (kick all players) and try again.",
        )
