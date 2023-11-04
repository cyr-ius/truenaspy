"""TrueNAS API."""
from __future__ import annotations

import asyncio
import socket
from logging import getLogger
from typing import Any

import aiohttp  # [import-error]

from .exceptions import TruenasException
from .helper import json_loads

_LOGGER = getLogger(__name__)

API_PATH = "api/v2.0"


class TrueNASConnect(object):
    """Handle all communication with TrueNAS."""

    def __init__(
        self,
        host: str,
        token: str,
        use_ssl: bool,
        verify_ssl: bool,
        timeout: int = 120,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the TrueNAS API."""
        self._protocol = "https" if use_ssl else "http"
        self._host = host
        self._url = f"{self._protocol}://{host}/{API_PATH}"
        self._token = token
        self._verify_ssl = verify_ssl
        self._timeout = timeout

        self.session = session
        self.close_session = False

    async def async_request(self, path: str, method: str = "GET", **kwargs: Any) -> Any:
        """Make a request."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
            self.close_session = True

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
            raise TruenasException("Timeout occurred while connecting.") from error
        except (aiohttp.ClientError, socket.gaierror) as error:
            raise TruenasException(
                f"Error occurred while communicating with Truenas. ({error})"
            ) from error

        try:
            data: Any = await response.json(loads=json_loads)
            _LOGGER.debug("TrueNAS %s query response: %s", self._host, data)
            return data
        except ValueError as error:
            raise TruenasException(error) from error
