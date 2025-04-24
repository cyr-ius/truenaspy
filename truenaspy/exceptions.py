"""Exceptions for Truenas connect."""


class TruenasException(Exception):
    """General exception."""


class WebsocketError(Exception):
    """General exception."""


class CallbackFailed(WebsocketError):
    """General exception."""


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
