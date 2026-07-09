"""DataUpdateCoordinator for the DiscoPanel integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
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

        self._async_purge_stale_devices(set(result))
        return result

    def _async_purge_stale_devices(self, live_server_ids: set[str]) -> None:
        """Remove HA devices for servers that no longer exist in DiscoPanel.

        When a server is deleted in the panel it disappears from the API, but
        its device (and entities) would otherwise linger in Home Assistant.
        The hub device (identified by the entry id) is always kept.
        """
        device_registry = dr.async_get(self.hass)
        entry_id = self.entry.entry_id
        for device in dr.async_entries_for_config_entry(device_registry, entry_id):
            server_id = next(
                (
                    identifier
                    for domain, identifier in device.identifiers
                    if domain == DOMAIN and identifier != entry_id
                ),
                None,
            )
            # Skip the hub device (no per-server identifier) and any device
            # whose server is still present.
            if server_id is None or server_id in live_server_ids:
                continue
            _LOGGER.debug(
                "Removing device for deleted DiscoPanel server %s", server_id
            )
            device_registry.async_update_device(
                device.id, remove_config_entry_id=entry_id
            )
