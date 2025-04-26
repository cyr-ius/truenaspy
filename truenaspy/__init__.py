# -*- coding:utf-8 -*-

"""Truenaspy package."""

from .api import TruenasClient
from .exceptions import (
    AuthenticationFailed,
    ConnectionError,
    ExecutionFailed,
    NotFoundError,
    TimeoutExceededError,
    TruenasException,
    WebsocketError,
)
from .subscription import Events
from .websocket import TruenasWebsocket

__all__ = [
    "AuthenticationFailed",
    "ConnectionError",
    "Events",
    "NotFoundError",
    "TimeoutExceededError",
    "TruenasClient",
    "TruenasException",
    "TruenasWebsocket",
    "WebsocketError",
    "ExecutionFailed",
]
