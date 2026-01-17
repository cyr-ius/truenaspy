"""Class for websocket."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
import json
import logging
import socket
import ssl
from types import TracebackType
from typing import Any
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
from .exceptions import (
    AuthenticationFailed,
    ExecutionFailed,
    TimeoutExceededError,
    WebsocketError,
)

logger = logging.getLogger(__name__)


class TruenasWebsocket:
    """Websocket class."""

    def __init__(
        self,
        host: str,
        port: int | None = None,
        use_tls: bool = True,
        verify_ssl: bool = True,
        session: ClientSession | None = None,
    ) -> None:
        """Initialize the websocket."""

        self.ws: ClientWebSocketResponse | None = None

        self._host = host
        self._scheme = "wss" if use_tls else "ws"
        self._port = WSS_PORT if use_tls else WS_PORT
        self._port = port if port else self._port
        self._verify_ssl = verify_ssl
        self._session: ClientSession = session or ClientSession()
        self._session_owner = session is None
        self._heartbeat_task: asyncio.Task[Any] | None = None
        self._listener_task: asyncio.Task[Any] | None = None
        self._login_status: str | None = None

        # Store futures waiting for websocket responses
        self._pendings: dict[str, asyncio.Future[Any]] = {}

        # Store event callbacks
        self._event_callbacks: dict[
            str, list[Callable[[Any], Coroutine[Any, Any, None]]]
        ] = {}

    @property
    def is_connected(self) -> bool:
        """Return if we are connect to the WebSocket."""
        return self.ws is not None and not self.ws.closed

    @property
    def is_logged(self) -> bool:
        """Return if we are connect to the WebSocket."""
        return self._login_status == LOGIN_SUCCESS

    async def _create_ssl_context(self, verify_ssl: bool) -> ssl.SSLContext:
        """Create SSL context for the websocket connection."""
        context = await asyncio.to_thread(ssl.create_default_context)
        if verify_ssl is False:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        return context

    async def _async_heartbeat(self) -> None:
        """Heartbeat websocket."""
        while self.ws and not self.ws.closed:
            try:
                await self.async_ping()
            except Exception as e:
                logger.warning(f"Heartbeat ping failed: {e}")
            await asyncio.sleep(WS_PING_INTERVAL)

    async def async_connect(self, username: str, password: str) -> asyncio.Task[Any]:
        """Connect to the websocket.

        Args:
            username: TrueNAS username
            password: TrueNAS password

        Returns:
            Listener task that processes incoming messages

        Raises:
            WebsocketError: If connection fails
            AuthenticationFailed: If login fails
        """

        # SSL context
        ssl_context = (
            await self._create_ssl_context(self._verify_ssl)
            if self._scheme == "wss"
            else False
        )

        uri = f"{self._scheme}://{self._host}:{self._port}{ENDPOINT}"
        try:
            self.ws = await self._session.ws_connect(uri, ssl=ssl_context)
        except (aiohttp.ClientError, socket.gaierror) as error:
            logger.error(f"Failed to connect to websocket: {error}")
            if self._session_owner and self._session:
                await self._session.close()
            raise WebsocketError(error) from error
        else:
            logger.debug("Connected to websocket")

            # Listen for events
            self._listener_task = asyncio.create_task(
                self._async_listen(), name="truenaspy_ws_listen"
            )

            # Login
            await self._async_handle_login(username, password)

            # Heartbeat
            self._heartbeat_task = asyncio.create_task(self._async_heartbeat())

            return self._listener_task

    async def _async_listen(self) -> None:
        """Listen for events on the WebSocket."""

        if not self.ws:
            raise WebsocketError("WebSocket not connected")

        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._async_handle_message(msg.data)
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.info("WebSocket connection closed by server")
                    break
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {msg.data}")
                    break
        except asyncio.CancelledError:
            logger.debug("Listener task cancelled")
            raise
        except (aiohttp.ClientError, json.JSONDecodeError) as e:
            logger.exception(f"Error in WebSocket listener: {e}")
            raise WebsocketError(f"WebSocket error: {e}") from e
        finally:
            for future in self._pendings.values():
                if not future.done():
                    future.set_exception(WebsocketError("WebSocket connection closed"))
            self._pendings.clear()

    async def _async_handle_message(self, data: Any) -> None:
        """Handle incoming messages from the WebSocket."""

        message = json.loads(data)
        logger.debug(f"Received message: {message}")

        if "id" in message:
            future = self._pendings.pop(message.get("id"), None)
            if future:
                if "result" in message:
                    future.set_result(message["result"])
                elif "error" in message:
                    future.set_exception(ExecutionFailed(message["error"]))
                else:
                    logger.warning(f"Response without result or error: {message}")
        elif "method" in message and "params" in message:
            await self._async_handle_event(message.get("params"))

    async def _async_handle_event(self, params: Any) -> None:
        """Handle incoming events from the WebSocket."""
        event_type = params.get("collection")

        # Get callbacks for specific event or wildcard
        callbacks = self._event_callbacks.get(event_type, [])
        if not callbacks and "*" in self._event_callbacks:
            callbacks = self._event_callbacks["*"]

        for callback in callbacks:
            task = asyncio.create_task(callback(params))
            task.add_done_callback(self._log_task_exception)

    def _log_task_exception(self, task: asyncio.Task[Any]) -> None:
        """Log exceptions from event callback tasks."""
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception(f"Unhandled exception in event callback: {e}")

    async def async_call(
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

        future = asyncio.get_running_loop().create_future()
        self._pendings[msg_id] = future

        try:
            await self.ws.send_json(message)
            logger.debug(f"Sent message: {message}")
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            self._pendings.pop(msg_id, None)
            raise TimeoutExceededError(f"Timeout on websocket: {method}")
        except Exception:
            self._pendings.pop(msg_id, None)
            if not future.done():
                future.cancel()
            raise

    async def _async_handle_login(self, username: str, password: str) -> None:
        """Login to the WebSocket."""

        payload = {
            "mechanism": "PASSWORD_PLAIN",
            "username": username,
            "password": password,
        }

        try:
            response = await self.async_call(method="auth.login_ex", params=payload)
            self._login_status = response.get("response_type")
            if not self.is_logged:
                raise AuthenticationFailed("Login failed")
        except TimeoutExceededError as error:
            self._login_status = None
            raise AuthenticationFailed(f"Login timeout ({error})") from error
        except ExecutionFailed as error:
            self._login_status = None
            raise AuthenticationFailed(f"Login timeout ({error})") from error

    async def async_ping(self) -> None:
        """Send ping."""

        await self.async_call(method="core.ping")

    async def async_subscribe(
        self, event: str, callback: Callable[[Any], Coroutine[Any, Any, None]]
    ) -> None:
        """Subscribe to a TrueNAS event and register a callback."""

        # Register callback
        if event not in self._event_callbacks:
            self._event_callbacks[event] = []

        self._event_callbacks[event].append(callback)

        # Send the subscribe message
        await self.async_call("core.subscribe", [event])
        logger.debug(f"Subscribed to event: {event}")

    async def async_subscribe_once(
        self, event: str, callback: Callable[[Any], Coroutine[Any, Any, None]]
    ) -> None:
        """Subscribe to a TrueNAS event, trigger callback once, then auto-unsubscribe."""

        async def one_time_callback(params: Any) -> None:
            """One-time callback for event subscription."""
            try:
                await callback(params)
            finally:
                # Remove callback after first execution
                if (
                    event in self._event_callbacks
                    and one_time_callback in self._event_callbacks[event]
                ):
                    self._event_callbacks[event].remove(one_time_callback)
                    if not self._event_callbacks[event]:
                        del self._event_callbacks[event]

        await self.async_subscribe(event, one_time_callback)

    async def async_unsubscribe(self, event: str) -> None:
        """Unsubscribe from a events."""
        # Unsubscribe from all events
        if event == "*":
            self._event_callbacks.clear()
            await self.async_call("core.unsubscribe", ["*"])
            logger.debug("Unsubscribed from all events")
        elif event in self._event_callbacks:
            del self._event_callbacks[event]
            await self.async_call("core.unsubscribe", [event])
            logger.debug(f"Unsubscribed from event: {event}")
        else:
            logger.debug(f"Event {event} not found in subscriptions")

    async def async_close(self) -> None:
        """Close the WebSocket connection."""

        # Call tasks
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        self._heartbeat_task = None

        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        self._listener_task = None

        # Cancel all pending futures
        for future in self._pendings.values():
            if not future.done():
                future.cancel()

        self._pendings.clear()

        # Close Websocket
        if self.ws and not self.ws.closed:  # Vérifier si pas déjà fermé
            await self.ws.close()
        self.ws = None
        self._login_status = None

        # Close session
        if self._session and self._session_owner:
            await self._session.close()

    async def __aenter__(self) -> TruenasWebsocket:
        """Enter the runtime context related to this object."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        exc_tb: TracebackType | None = None,
    ) -> None:
        """Exit the runtime context related to this object."""
        await self.async_close()
        if exc_type is not None:
            logger.exception("Exception in WebSocket context", exc_info=exc_val)
        else:
            logger.debug("Exited WebSocket context")
