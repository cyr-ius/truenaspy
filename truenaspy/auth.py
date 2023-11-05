"""TrueNAS API."""
from __future__ import annotations

import asyncio
import socket
from logging import getLogger
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

from .exceptions import TruenasAuthenticationError, TruenasConnectionError, TruenasError
from .helper import json_loads

_LOGGER = getLogger(__name__)

API_PATH = "api/v2.0"


class Auth(object):
    """Handle all communication with TrueNAS."""

    def __init__(
        self,
        host: str,
        token: str,
        use_ssl: bool,
        verify_ssl: bool,
        timeout: int = 120,
        session: ClientSession | None = None,
    ) -> None:
        """Initialize the TrueNAS API."""
        self._host = host
        self._protocol = "https" if use_ssl else "http"
        self._timeout = timeout
        self._token = token
        self._url = f"{self._protocol}://{host}/{API_PATH}"
        self._verify_ssl = verify_ssl
        self._close_session = False
        self.session = session

    async def async_request(self, path: str, method: str = "GET", **kwargs: Any) -> Any:
        """Make a request."""
        if self.session is None:
            self.session = ClientSession()
            self._close_session = True

        headers = kwargs.pop("headers", {})
        headers.update(
            {
                "Accept": "application/json",
                "Authorization": f"Bearer {self._token}",
            }
        )
        try:
            _LOGGER.debug("TrueNAS %s query: %s (%s)", self._host, path, method)
            async with asyncio.timeout(self._timeout):
                response = await self.session.request(
                    method,
                    f"{self._url}/{path}",
                    **kwargs,
                    headers=headers,
                    verify_ssl=self._verify_ssl,
                )
                response.raise_for_status()
        except (asyncio.CancelledError, asyncio.TimeoutError) as error:
            msg = "Timeout occurred while connecting to the Truenas API"
            raise TruenasConnectionError(msg) from error
        except ClientResponseError as error:
            if error.status in [401, 403]:
                msg = "Authentication to the Truenas API failed"
                raise TruenasAuthenticationError(msg) from error
            msg = "Error occurred while communicating with Truenas."
            raise TruenasError(msg) from error
        except (ClientError, socket.gaierror) as error:
            msg = "Error occurred while communicating with Truenas."
            raise TruenasError(msg) from error

        try:
            data: Any = await response.json(loads=json_loads)
            _LOGGER.debug("TrueNAS %s query response: %s", self._host, data)
            return data
        except ValueError as error:
            msg = "The Truenas API response is not formatted correctly"
            raise TruenasError(error) from error

    async def async_close(self) -> None:
        """Close open client session."""
        if self.session and self._close_session:
            await self.session.close()
