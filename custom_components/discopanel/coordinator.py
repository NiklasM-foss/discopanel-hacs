"""DataUpdateCoordinator for the DiscoPanel integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    DiscoPanelApi,
    DiscoPanelAuthError,
    DiscoPanelConnectionError,
    DiscoPanelError,
)
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class DiscoPanelDataUpdateCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Coordinator that polls DiscoPanel for all servers."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: DiscoPanelApi,
    ) -> None:
        """Initialize the coordinator."""
        self.api = api
        self.entry = entry

        scan_interval = entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        try:
            scan_interval = int(scan_interval)
        except (TypeError, ValueError):
            scan_interval = DEFAULT_SCAN_INTERVAL
        if scan_interval < MIN_SCAN_INTERVAL:
            scan_interval = MIN_SCAN_INTERVAL

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch all servers and index them by id."""
        try:
            servers = await self.api.list_servers(full_stats=True)
        except DiscoPanelAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except DiscoPanelConnectionError as err:
            raise UpdateFailed(str(err)) from err
        except DiscoPanelError as err:
            raise UpdateFailed(str(err)) from err

        result: dict[str, dict[str, Any]] = {}
        for server in servers:
            server_id = server.get("id")
            if isinstance(server_id, str) and server_id:
                result[server_id] = server
        return result
