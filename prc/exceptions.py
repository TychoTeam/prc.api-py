"""

All exceptions in use by the prc.api package.

"""

# Base Exception

from typing import Optional


class PRCException(Exception):
    """Base exception, can be used to catch all package exception."""

    def __init__(self, message: str):
        super().__init__(message)


class APIException(PRCException):
    """Base exception to catch all PRC API error responses."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message

        super().__init__(f"({code}) {message}")


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
