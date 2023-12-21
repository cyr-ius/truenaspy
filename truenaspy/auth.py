"""TrueNAS API."""
from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass, field
from logging import getLogger
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

from .exceptions import (
    TruenasAuthenticationError,
    TruenasConnectionError,
    TruenasError,
    TruenasNotFoundError,
)
from .helper import json_loads

_LOGGER = getLogger(__name__)

API_PATH = "api/v2.0"


@dataclass
class Auth:
    """Handle all communication with TrueNAS."""

    host: str
    api_key: str
    use_ssl: bool
    verify_ssl: bool
    timeout: int = 120
    session: ClientSession | None = None

    _protocol: str = field(init=False)
    _close_session: bool = False
    _url: str = field(init=False)

    def __post_init__(self) -> None:
        self._protocol: str = "https" if self.use_ssl else "http"
        self._url = f"{self._protocol}://{self.host}/{API_PATH}"

    async def async_request(self, path: str, method: str = "GET", **kwargs: Any) -> Any:
        """Make a request."""
        if self.session is None:
            self.session = ClientSession()
            self._close_session = True

        headers = kwargs.pop("headers", {})
        headers.update(
            {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
        )
        try:
            _LOGGER.debug("TrueNAS %s query: %s (%s)", self.host, path, method)
            _LOGGER.debug("POST Content: %s", kwargs.get("json"))
            async with asyncio.timeout(self.timeout):
                response = await self.session.request(
                    method,
                    f"{self._url}/{path}",
                    **kwargs,
                    headers=headers,
                    verify_ssl=self.verify_ssl,
                )
                response.raise_for_status()
        except (asyncio.CancelledError, asyncio.TimeoutError) as error:
            msg = "Timeout occurred while connecting to the Truenas API"
            raise TruenasConnectionError(msg) from error
        except ClientResponseError as error:
            if error.status in [401, 403]:
                msg = "Authentication to the Truenas API failed"
                raise TruenasAuthenticationError(msg) from error
            if error.status in [404]:
                msg = f"API not found ({path} - {error.status})"
                raise TruenasNotFoundError(msg) from error
            msg = f"Error occurred while communicating with Truenas ({error})"
            raise TruenasError(msg) from error
        except (ClientError, socket.gaierror) as error:
            msg = "Error occurred while communicating with Truenas"
            raise TruenasError(msg) from error

        try:
            data: Any = await response.json(loads=json_loads)
            _LOGGER.debug("TrueNAS %s query response: %s", self.host, data)
            return data
        except ValueError as error:
            msg = "The Truenas API response is not formatted correctly"
            raise TruenasError(error) from error

    async def async_close(self) -> None:
        """Close open client session."""
        if self.session and self._close_session:
            await self.session.close()
