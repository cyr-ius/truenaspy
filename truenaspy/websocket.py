"""Class for websocket."""

from __future__ import annotations

import asyncio
import json
import logging
import socket
import ssl
from types import TracebackType
from typing import Any, Awaitable, Callable, Type
import uuid

import aiohttp
from aiohttp import ClientSession, ClientWebSocketResponse

from .const import (
    ENDPOINT,
    JSON_RPC_VERSION,
    LOGIN_SUCCESS,
    WS_PING_INTERVAL,
    WS_PORT,
    WSS_PORT,
)
from .exceptions import AuthenticationFailed, TimeoutExceededError, WebsocketError

logger = logging.getLogger(__name__)


class Websocket:
    """Websocket class."""

    def __init__(
        self,
        host: str,
        port: int | None = None,
        use_tls: bool = True,
        session: ClientSession | None = None,
    ) -> None:
        """Initialize the websocket."""

        self.ws: ClientWebSocketResponse | None = None
        self._session = session or ClientSession()

        self._host = host
        self._scheme = "wss" if use_tls else "ws"
        self._port = WSS_PORT if use_tls else WS_PORT
        self._port = port if port else self._port

        # Login status
        self._login_status: str | None = None

        # Accept self-signed certificates
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

        # Store futures waiting for websocket responses
        self._pendings: dict[str, asyncio.Future[Any]] = {}

        # Store event callbacks
        self._event_callbacks: dict[str, list[Callable[[Any], Awaitable[None]]]] = {}

    @property
    def is_connected(self) -> bool:
        """Return if we are connect to the WebSocket."""
        return self.ws is not None and not self.ws.closed

    @property
    def is_logged(self) -> bool:
        """Return if we are connect to the WebSocket."""
        return self._login_status == LOGIN_SUCCESS

    async def _async_heartbeat(self) -> None:
        """Heartbeat websocket."""
        while self.ws and not self.ws.closed:
            await self.async_ping()
            await asyncio.sleep(WS_PING_INTERVAL)

    async def async_connect(self) -> None:
        """Connect to the websocket."""

        if not self._session:
            raise WebsocketError("Session not found")

        uri = f"{self._scheme}://{self._host}:{self._port}{ENDPOINT}"
        try:
            self.ws = await self._session.ws_connect(uri, ssl=self.ssl_context)
        except (aiohttp.ClientError, socket.gaierror) as e:
            logger.error(f"Failed to connect to websocket: {e}")
            if self._session:
                await self._session.close()
            raise WebsocketError(e)
        else:
            logger.debug(f"Connected to websocket ({uri})")
            asyncio.create_task(self.async_listen())

    async def async_listen(self) -> None:
        """Listen for events on the WebSocket."""
        if not self.ws:
            raise WebsocketError("WebSocket not connected")

        async for msg in self.ws:
            try:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    logger.debug(f"Received message: {data}")
                    # Match by ID and set result to the future
                    msg_id = data.get("id")
                    if msg_id and msg_id in self._pendings:
                        future = self._pendings.pop(msg_id)
                        if "error" in data:
                            future.set_exception(Exception(data["error"]))
                        else:
                            future.set_result(data["result"])
                    # Handle notifications with no ID (event push)
                    elif data.get("method") == "collection_update":
                        event_type = data.get("params", {}).get("collection")
                        args = data.get("params")

                        if (
                            event_type not in self._event_callbacks
                            and "*" in self._event_callbacks
                        ):
                            event_type = "*"

                        if event_type in self._event_callbacks:
                            for callback in self._event_callbacks[event_type]:
                                try:
                                    asyncio.create_task(callback(args))  # type: ignore[arg-type]
                                except Exception as e:
                                    logger.warning(f"Error in event callback: {e}")
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"Error: {msg.data}")
            except aiohttp.ClientError as e:
                logger.error(f"WebSocket error: {e}")
                raise WebsocketError(f"WebSocket error: {e}")
            except json.JSONDecodeError:
                logger.warning("Received invalid JSON")
                raise WebsocketError("Received invalid JSON")
            except asyncio.TimeoutError:
                logger.warning("WebSocket timeout")
                raise TimeoutExceededError("WebSocket timeout")

    async def async_send_msg(
        self, method: str, params: Any | None = None, timeout: float = 10.0
    ) -> Any:
        """Send a message to the WebSocket with timeout."""

        if not self.ws:
            raise WebsocketError("WebSocket not connected")

        if params is None:
            params = []

        if not isinstance(params, list):
            params = [params]

        msg_id = str(uuid.uuid4())
        message = {
            "jsonrpc": JSON_RPC_VERSION,
            "id": msg_id,
            "method": method,
            "params": params,
        }

        future = asyncio.get_event_loop().create_future()
        self._pendings[msg_id] = future

        try:
            await self.ws.send_json(message)
            logger.debug(f"Sent message: {message}")
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            self._pendings.pop(msg_id, None)
            logger.warning(f"Timeout on RPC call: {method}")
            raise TimeoutExceededError(f"Timeout on websocket: {method}")

    async def async_login(self, username: str, password: str | None = None) -> None:
        """Login to the WebSocket."""
        if not self.ws:
            raise WebsocketError("WebSocket not connected")

        payload = {
            "mechanism": "PASSWORD_PLAIN",
            "username": username,
            "password": password,
        }

        try:
            response = await self.async_send_msg(method="auth.login_ex", params=payload)
            self._login_status = response.get("response_type")
            if not self.is_logged:
                raise AuthenticationFailed("Login failed")
        except TimeoutExceededError:
            logger.error("Login timeout")
            self._logged = False
            raise AuthenticationFailed("Login timeout")
        else:
            logger.debug("Logged in to websocket")
            asyncio.create_task(self._async_heartbeat())

    async def async_ping(self) -> None:
        """Send ping."""
        await self.async_send_msg(method="core.ping")

    async def async_subscribe(
        self, event: str, callback: Callable[[Any], Awaitable[None]]
    ) -> None:
        """Subscribe to a TrueNAS event and register a callback."""

        # Register callback
        if event not in self._event_callbacks:
            self._event_callbacks[event] = []
        self._event_callbacks[event].append(callback)

        # Send the subscribe message
        await self.async_send_msg("core.subscribe", [event])
        logger.debug(f"Subscribed to event: {event}")

    async def async_subscribe_once(
        self, event: str, callback: Callable[[Any], Awaitable[None]]
    ) -> None:
        """Subscribe to a TrueNAS event, trigger callback once, then auto-unsubscribe."""

        async def one_time_callback(*args: Any) -> None:
            """One-time callback for event subscription."""
            try:
                await callback(*args)
            finally:
                # Remove callback after first execution
                if event in self._event_callbacks:
                    self._event_callbacks[event].remove(one_time_callback)
                    if not self._event_callbacks[event]:
                        del self._event_callbacks[event]

        await self.async_subscribe(event, one_time_callback)

    async def async_close(self) -> None:
        """Close the WebSocket connection."""
        if self.ws:
            await self.ws.close()
            self.ws = None
            self._login_status = None
            logger.debug("WebSocket closed")
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("Session closed")

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        exc_tb: TracebackType | None = None,
    ) -> None:
        """Exit the runtime context related to this object."""
        await self.async_close()
        if exc_type is not None:
            assert exc_val is not None
            logger.error(f"Exception in WebSocket: {exc_val}")
            raise exc_val
        logger.debug("Exited WebSocket context")
