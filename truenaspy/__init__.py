# -*- coding:utf-8 -*-

"""Truenaspy package."""

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
    "TruenasException",
    "TruenasWebsocket",
    "WebsocketError",
    "ExecutionFailed",
]
