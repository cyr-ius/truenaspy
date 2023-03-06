"""TrueNAS API."""
from __future__ import annotations

from logging import getLogger
from typing import Any

from aiohttp import ClientError, ClientSession

_LOGGER = getLogger(__name__)

API_PATH = "api/v2.0"


class TrueNASConnect(object):
    """Handle all communication with TrueNAS."""

    def __init__(
        self,
        session: ClientSession,
        host: str,
        token: str,
        use_ssl: bool,
        verify_ssl: bool,
    ) -> None:
        """Initialize the TrueNAS API."""
        self._protocol = "https" if use_ssl else "http"
        self._session = session
        self._host = host
        self._url = f"{self._protocol}://{host}/{API_PATH}"
        self._token = token
        self._verify_ssl = verify_ssl

    async def async_request(
        self, path: str, method: str = "GET", **kwargs: Any
    ) -> dict[str, Any]:
        """Make a request."""
        if headers := kwargs.pop("headers", {}):
            headers = dict(headers)

        headers.update(
            {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }
        )
        try:
            _LOGGER.debug("TrueNAS %s query: %s", self._host, path)
            response = await self._session.request(
                method,
                f"{self._url}/{path}",
                **kwargs,
                headers=headers,
                verify_ssl=self._verify_ssl,
            )
            if response.status == 200:
                data: dict[str, Any] = await response.json()
                _LOGGER.debug("TrueNAS %s query response: %s", self._host, data)
                return data
            else:
                _LOGGER.error("%s %s", response.status, response.reason)
                return {"error": f"{response.status} {response.reason}"}
        except ClientError as error:
            _LOGGER.error(error)
            return {"error": str(error)}
        except Exception as error:  # pylint: disable=broad-exception-caught
            _LOGGER.error(error)
            return {"error": str(error)}
