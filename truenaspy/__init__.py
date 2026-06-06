# -*- coding:utf-8 -*-

"""Truenaspy package."""

from .exceptions import (
    AuthenticationFailed,
    ExecutionFailed,
    NotFoundError,
    TimeoutExceededError,
    TruenasConnectionError,
    TruenasException,
    WebsocketError,
)

from .websocket import TruenasWebsocket

__all__ = [
    "AuthenticationFailed",
    "ExecutionFailed",
    "NotFoundError",
    "TimeoutExceededError",
    "TruenasConnectionError",
    "TruenasException",
    "TruenasWebsocket",
    "WebsocketError",
]
