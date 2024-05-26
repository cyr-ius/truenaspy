"""TrueNAS API."""

from __future__ import annotations

import asyncio
from logging import getLogger
import socket
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

from .exceptions import (
    AuthenticationFailed,
    NotFoundError,
    TimeoutExceededError,
    TruenasException,
    UnexpectedResponse,
)
from .helper import json_loads

_LOGGER = getLogger(__name__)

API_PATH = "api/v2.0"


class Auth:
    """Handle all communication with TrueNAS."""

    _close_session: bool = False

    def __init__(
        self,
        session: ClientSession,
        host: str,
        token: str,
        use_ssl: bool = False,
        verify_ssl: bool = True,
        timeout: int = 120,
    ) -> None:
        scheme = "https" if use_ssl else "http"
        self._url = f"{scheme}://{host}/{API_PATH}"
        self._verify_ssl = verify_ssl
        self._access_token = token
        self._timeout = timeout
        self._session = session

    async def async_request(self, path: str, method: str = "get", **kwargs: Any) -> Any:
        """Make a request."""
        kwargs.setdefault("headers", {})
        kwargs.setdefault("verify_ssl", self._verify_ssl)
        kwargs["headers"].update(
            {
                "Accept": "application/json",
                "Authorization": f"Bearer {self._access_token}",
            }
        )
        try:
            async with asyncio.timeout(self._timeout):
                _LOGGER.debug(
                    "Url: %s (%s) - Content: %s", path, method, kwargs.get("json")
                )
                response = await self._session.request(
                    method, f"{self._url}/{path}", **kwargs
                )
                response.raise_for_status()
        except (asyncio.CancelledError, asyncio.TimeoutError) as error:
            msg = "Timeout occurred while connecting to the Truenas API"
            raise TimeoutExceededError(msg) from error
        except ClientResponseError as error:
            if error.status in [401, 403]:
                msg = "Authentication to the Truenas API failed"
                raise AuthenticationFailed(msg) from error
            if error.status in [404]:
                msg = f"API not found ({path} - {error.status})"
                raise NotFoundError(msg) from error
            msg = f"Error occurred while communicating with Truenas ({error})"
            raise TruenasException(msg) from error
        except (ClientError, socket.gaierror) as error:
            msg = "Error occurred while communicating with Truenas"
            raise TruenasException(msg) from error

        try:
            data = await response.json(loads=json_loads)
            _LOGGER.debug("Response: %s", data)
            return data
        except ValueError as error:
            msg = "The Truenas API response is not formatted correctly"
            raise UnexpectedResponse(f"Error while decoding Json ({error})") from error
