"""Exceptions for Truenas connect."""


class TruenasException(Exception):
    """General exception."""


class WebsocketError(TruenasException):
    """General exception."""


class ExecutionFailed(WebsocketError):
    """Command exception."""


class ConnectionError(TruenasException):
    """Connection exception."""


class AuthenticationFailed(TruenasException):
    """Authentication exception."""


class NotFoundError(TruenasException):
    """API not found exception."""


class TimeoutExceededError(TruenasException):
    """Timeout exception."""


class UnexpectedResponse(TruenasException):
    """Timeout exception."""
