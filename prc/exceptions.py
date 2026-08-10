"""

All exceptions in use by the prc.api package.

"""

# Base Exception

from typing import Dict, Optional, Type
import httpx


class PRCException(Exception):
    """Base exception for all package exception."""

    def __init__(self, message: str):
        super().__init__(message)


class HTTPException(PRCException):
    """Base exception for all HTTP-level response errors."""

    def __init__(self, message: str, response: httpx.Response):
        self.message = message
        self.status_code = response.status_code

        super().__init__(f"[{self.status_code}] {message}")

    def is_server_error(self) -> bool:
        """Whether the response status is a `5XX`."""

        return self.status_code >= 500 and self.status_code <= 599

    def is_client_error(self) -> bool:
        """Whether the response status is a `4XX`."""

        return self.status_code >= 400 and self.status_code <= 499

    def __str__(self):
        return f"[HTTP {self.status_code}] {self.message}"


class APIException(PRCException):
    """Base exception for all PRC API error responses."""

    def __init__(
        self,
        *,
        code: int,
        message: str,
        response: Optional[httpx.Response] = None,
        body: Optional[Dict] = None,
    ):
        self.code = code
        self.message = message

        self.response = response
        self.body = body

        super().__init__(message)

    def __str__(self):
        return f"[HTTP {self.response.status_code if self.response else 0}] ({self.code}) {self.message}\n\t{self.body}"


# Generic Exceptions


class RequestTimeout(PRCException):
    """Exception raised when a HTTP request times out and is not fulfilledd."""

    def __init__(self, retry: int, max_retries: int, timeout: float):
        self.retry = retry
        self.max_retries = max_retries
        self.timeout = timeout

        super().__init__(
            f"PRC API took too long to respond. ({retry}/{max_retries} retries) ({timeout}s timeout)"
        )


# API Exceptions


class UnknownError(APIException):
    """Exception raised when an unknown server-side error occurs. If this persists, contact PRC via an API ticket."""

    code = 0


class CommunicationError(APIException):
    """Exception raised when a server-side error occurs while communicating with Roblox and/or the in-game private server."""

    code = 1001


class InternalError(APIException):
    """Exception raised when an internal server-side error occurs."""

    code = 1002


class InvalidServerKey(APIException):
    """Exception raised when the server-key is invalid or has expired."""

    code = 2002


class InvalidGlobalKey(APIException):
    """Exception raised when the global API key is invalid or has expired."""

    code = 2003


class BannedServerKey(APIException):
    """Exception raised when the server-key is banned from accessing the API."""

    code = 2004


class InvalidCommand(APIException):
    """Exception raised when an invalid command is sent."""

    code = 3001


class ServerOffline(APIException):
    """Exception raised when the server being reached is currently offline (has no players)."""

    code = 3002


class ProhibitedAction(APIException):
    """Exception raised when a prohibited action is attempted."""

    code = 4000


class RateLimited(APIException):
    """Exception raised when a rate limit is exceeded. The package handles automatically handles rate limits; this should only occur when other applications are using the same IP as you."""

    code = 4001


class RestrictedCommand(APIException):
    """Exception raised when a restricted command is sent."""

    code = 4002


class ProhibitedMessage(APIException):
    """Exception raised when a prohibited message is sent."""

    code = 4003


class RestrictedResource(APIException):
    """Exception raised when attempting to access a restricted resource."""

    code = 9998


class OutOfDateModule(APIException):
    """Exception raised when the module running in the in-game private server is out of date. To resolve this, all players must be removed (i.e, server must be restarted)."""

    code = 9999


ERROR_CODE_MAP: Dict[int, Type[APIException]] = {
    0: UnknownError,
    1001: CommunicationError,
    1002: InternalError,
    2002: InvalidServerKey,
    2003: InvalidGlobalKey,
    2004: BannedServerKey,
    3001: InvalidCommand,
    3002: ServerOffline,
    4000: ProhibitedAction,
    4001: RateLimited,
    4002: RestrictedCommand,
    4003: ProhibitedMessage,
    9998: RestrictedResource,
    9999: OutOfDateModule,
}
