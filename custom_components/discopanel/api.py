"""API client for the DiscoPanel ConnectRPC (HTTP/JSON) backend."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10

# ConnectRPC service names.
_SERVER_SERVICE = "discopanel.v1.ServerService"
_AUTH_SERVICE = "discopanel.v1.AuthService"


class DiscoPanelError(Exception):
    """Generic DiscoPanel error."""


class DiscoPanelAuthError(DiscoPanelError):
    """Raised when authentication fails (HTTP 401 / unauthenticated)."""


class DiscoPanelConnectionError(DiscoPanelError):
    """Raised when the DiscoPanel host cannot be reached."""


class DiscoPanelApi:
    """Thin async client around the DiscoPanel ConnectRPC JSON API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        token: str,
        use_ssl: bool = False,
        verify_ssl: bool = True,
    ) -> None:
        """Initialize the API client.

        The aiohttp session MUST be supplied by the caller
        (homeassistant.helpers.aiohttp_client.async_get_clientsession).
        """
        self._session = session
        self._host = host
        self._port = port
        self._token = token
        self._use_ssl = use_ssl
        self._verify_ssl = verify_ssl

        scheme = "https" if use_ssl else "http"
        self._base_url = f"{scheme}://{host}:{port}"

    @property
    def base_url(self) -> str:
        """Return the base URL of the DiscoPanel instance."""
        return self._base_url

    # ------------------------------------------------------------------
    # Low-level request helper.
    # ------------------------------------------------------------------
    async def _call(
        self,
        service: str,
        method: str,
        payload: dict[str, Any] | None = None,
        *,
        authed: bool = True,
    ) -> dict[str, Any]:
        """Perform a single ConnectRPC POST call and return the parsed JSON."""
        url = f"{self._base_url}/{service}/{method}"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if authed:
            headers["Authorization"] = f"Bearer {self._token}"

        body = payload if payload is not None else {}

        # verify_ssl only matters for https; for http it is ignored by aiohttp.
        ssl_param: bool | None = None
        if self._use_ssl and not self._verify_ssl:
            ssl_param = False

        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.post(
                    url,
                    json=body,
                    headers=headers,
                    ssl=ssl_param,
                ) as resp:
                    text = await resp.text()

                    if resp.status == 401:
                        raise DiscoPanelAuthError(
                            self._extract_message(text) or "invalid token"
                        )

                    if resp.status < 200 or resp.status >= 300:
                        message = self._extract_message(text) or (
                            f"HTTP {resp.status}"
                        )
                        raise DiscoPanelError(message)

                    if not text:
                        return {}
                    try:
                        data = await resp.json(content_type=None)
                    except (aiohttp.ContentTypeError, ValueError) as err:
                        raise DiscoPanelError(
                            f"Invalid JSON response: {err}"
                        ) from err
                    if not isinstance(data, dict):
                        raise DiscoPanelError("Unexpected non-object response")
                    return data
        except DiscoPanelError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise DiscoPanelConnectionError(
                f"Error connecting to DiscoPanel at {self._base_url}: {err}"
            ) from err

    @staticmethod
    def _extract_message(text: str) -> str | None:
        """Best-effort extraction of a Connect error message from a body."""
        if not text:
            return None
        try:
            import json

            data = json.loads(text)
        except ValueError:
            return text[:200]
        if isinstance(data, dict):
            msg = data.get("message")
            if isinstance(msg, str) and msg:
                return msg
        return None

    # ------------------------------------------------------------------
    # Public API methods.
    # ------------------------------------------------------------------
    async def get_auth_status(self) -> dict[str, Any]:
        """Public (no-auth) reachability + auth-config probe."""
        return await self._call(
            _AUTH_SERVICE, "GetAuthStatus", {}, authed=False
        )

    async def list_servers(self, full_stats: bool = True) -> list[dict[str, Any]]:
        """Return the list of server objects."""
        data = await self._call(
            _SERVER_SERVICE, "ListServers", {"fullStats": full_stats}
        )
        servers = data.get("servers")
        if not isinstance(servers, list):
            return []
        return [s for s in servers if isinstance(s, dict)]

    async def get_server(self, server_id: str) -> dict[str, Any]:
        """Return a single server object."""
        data = await self._call(_SERVER_SERVICE, "GetServer", {"id": server_id})
        server = data.get("server")
        if not isinstance(server, dict):
            raise DiscoPanelError(f"Server {server_id} not found in response")
        return server

    async def start_server(self, server_id: str) -> dict[str, Any]:
        """Start a server."""
        return await self._call(_SERVER_SERVICE, "StartServer", {"id": server_id})

    async def stop_server(self, server_id: str) -> dict[str, Any]:
        """Stop a server."""
        return await self._call(_SERVER_SERVICE, "StopServer", {"id": server_id})

    async def restart_server(self, server_id: str) -> dict[str, Any]:
        """Restart a server."""
        return await self._call(
            _SERVER_SERVICE, "RestartServer", {"id": server_id}
        )

    async def send_command(
        self, server_id: str, command: str, silent: bool = True
    ) -> dict[str, Any]:
        """Send a console command to a server."""
        return await self._call(
            _SERVER_SERVICE,
            "SendCommand",
            {"id": server_id, "command": command, "silent": silent},
        )

    async def get_server_logs(
        self, server_id: str, tail: int = 100
    ) -> dict[str, Any]:
        """Return recent server logs."""
        return await self._call(
            _SERVER_SERVICE, "GetServerLogs", {"id": server_id, "tail": tail}
        )
