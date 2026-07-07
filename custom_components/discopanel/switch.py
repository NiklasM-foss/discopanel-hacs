"""Switch platform for the DiscoPanel integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import DiscoPanelError
from .const import DOMAIN, is_running
from .coordinator import DiscoPanelDataUpdateCoordinator
from .entity import DiscoPanelServerEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DiscoPanel power switches from a config entry."""
    coordinator: DiscoPanelDataUpdateCoordinator = hass.data[DOMAIN][
        entry.entry_id
    ]

    known: set[str] = set()

    @callback
    def _add_new_entities() -> None:
        """Add switch entities for any newly discovered servers."""
        new_entities: list[DiscoPanelPowerSwitch] = []
        for server_id in coordinator.data or {}:
            if server_id in known:
                continue
            known.add(server_id)
            new_entities.append(
                DiscoPanelPowerSwitch(coordinator, server_id)
            )
        if new_entities:
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class DiscoPanelPowerSwitch(DiscoPanelServerEntity, SwitchEntity):
    """A power switch that starts/stops a DiscoPanel server."""

    _attr_translation_key = "server"
    _attr_icon = "mdi:minecraft"

    def __init__(
        self,
        coordinator: DiscoPanelDataUpdateCoordinator,
        server_id: str,
    ) -> None:
        """Initialize the power switch."""
        super().__init__(coordinator, server_id)
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_{server_id}_power"
        )

    @property
    def is_on(self) -> bool:
        """Return True if the server is running."""
        return is_running(self.server.get("status"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start the server."""
        try:
            await self.coordinator.api.start_server(self._server_id)
        except DiscoPanelError as err:
            raise HomeAssistantError(
                f"Failed to start server {self._server_id}: {err}"
            ) from err
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop the server."""
        try:
            await self.coordinator.api.stop_server(self._server_id)
        except DiscoPanelError as err:
            raise HomeAssistantError(
                f"Failed to stop server {self._server_id}: {err}"
            ) from err
        await self.coordinator.async_request_refresh()
