"""

Exceptions raised due to PRC API errors and some general exceptions

"""

# Base Exception


class PRCException(Exception):
    """Base exception to catch any prc.api exception"""

    def __init__(self, message: str):
        super().__init__(message)


class APIException(PRCException):
    """Base exception to catch PRC API exceptions"""

    def __init__(self, error_code: int, message: str):
        self.error_code = error_code
        self.message = message

        super().__init__(f"({error_code}) {message}")


# Exceptions


class UnknownError(APIException):
    """Exception raised when an unknown error occurs."""

    def __init__(self):
        super().__init__(
            0,
            "Unknown error occurred. If this is persistent, contact PRC via an API ticket.",
        )


class CommunicationError(APIException):
    """Exception raised when an error occurs communicating with Roblox / the in-game private server."""

    def __init__(self):
        super().__init__(
            1001,
            "An error occurred communicating with Roblox / the in-game private server.",
        )


class InternalError(APIException):
    """Exception raised when an internal system error occurs."""

    def __init__(self):
        super().__init__(1002, "An internal system error occurred.")


class MissingServerKey(APIException):
    """Exception raised when a server-key is not provided."""

    def __init__(self):
        super().__init__(2000, "You did not provide a server-key.")


class InvalidServerKeyFormat(APIException):
    """Exception raised when a server-key is incorrectly formatted."""

    def __init__(self):
        super().__init__(2001, "You provided an incorrectly formatted server-key.")


class InvalidServerKey(APIException):
    """Exception raised when a server-key is invalid or expired."""

    def __init__(self):
        super().__init__(2002, "You provided an invalid (or expired) server-key.")


class InvalidGlobalKey(APIException):
    """Exception raised when a global API key is invalid."""

    def __init__(self):
        super().__init__(2003, "You provided an invalid global API key.")


class BannedServerKey(APIException):
    """Exception raised when a server-key is banned from accessing the API."""

    def __init__(self):
        super().__init__(
            2004, "Your server-key is currently banned from accessing the API."
        )


class InvalidCommand(APIException):
    """Exception raised when a valid command is not provided in the request body."""

    def __init__(self):
        super().__init__(
            3001, "You did not provide a valid command in the request body."
        )


class ServerOffline(APIException):
    """Exception raised when the server being reached is currently offline."""

    def __init__(self):
        super().__init__(
            3002,
            "The server you are attempting to reach is currently offline (has no players).",
        )


class RateLimit(APIException):
    """Exception raised when rate limiting occurs."""

    def __init__(self):
        super().__init__(4001, "You are being rate limited.")


class RestrictedCommand(APIException):
    """Exception raised when a restricted command is attempted."""

    def __init__(self):
        super().__init__(4002, "The command you are attempting to run is restricted.")


class ProhibitedMessage(APIException):
    """Exception raised when a prohibited message is attempted to be sent."""

    def __init__(self):
        super().__init__(4003, "The message you're trying to send is prohibited.")


class RestrictedResource(APIException):
    """Exception raised when a restricted resource is accessed."""

    def __init__(self):
        super().__init__(9998, "The resource you are accessing is restricted.")


class OutOfDateModule(APIException):
    """Exception raised when the module running on the in-game server is out of date."""

    def __init__(self):
        super().__init__(
            9999,
            "The module running on the in-game server is out of date, please kick all and try again.",
        )
