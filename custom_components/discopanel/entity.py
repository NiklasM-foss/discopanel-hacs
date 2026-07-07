"""Base entity for the DiscoPanel integration."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    HUB_NAME,
    MANUFACTURER,
    mod_loader_pretty,
)
from .coordinator import DiscoPanelDataUpdateCoordinator


class DiscoPanelServerEntity(CoordinatorEntity[DiscoPanelDataUpdateCoordinator]):
    """Base class for all entities tied to a single DiscoPanel server."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DiscoPanelDataUpdateCoordinator,
        server_id: str,
    ) -> None:
        """Initialize the server entity."""
        super().__init__(coordinator)
        self._server_id = server_id

    @property
    def server_id(self) -> str:
        """Return the DiscoPanel server id."""
        return self._server_id

    @property
    def server(self) -> dict[str, Any]:
        """Return the current server dict from coordinator data.

        Returns an empty dict if the server is not currently present so that
        callers can safely use ``.get(...)`` without raising.
        """
        data = self.coordinator.data or {}
        return data.get(self._server_id) or {}

    @property
    def available(self) -> bool:
        """Return True if the coordinator succeeded and the server is known."""
        return (
            self.coordinator.last_update_success
            and self._server_id in (self.coordinator.data or {})
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info for this server, linked to the panel hub."""
        server = self.server
        name = server.get("name") or self._server_id
        mc_version = server.get("mcVersion")
        model = mod_loader_pretty(server.get("modLoader"))

        return DeviceInfo(
            identifiers={(DOMAIN, self._server_id)},
            name=name,
            manufacturer=MANUFACTURER,
            model=model,
            sw_version=mc_version,
            configuration_url=self.coordinator.api.base_url,
            via_device=(DOMAIN, self.coordinator.entry.entry_id),
        )

    @staticmethod
    def hub_device_info(
        entry_id: str, configuration_url: str | None = None
    ) -> DeviceInfo:
        """Return the DeviceInfo for the panel hub device."""
        return DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=HUB_NAME,
            manufacturer=MANUFACTURER,
            model="DiscoPanel",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=configuration_url,
        )
