"""Button platform for the DiscoPanel integration."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import DiscoPanelError
from .const import DOMAIN
from .coordinator import DiscoPanelDataUpdateCoordinator
from .entity import DiscoPanelServerEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DiscoPanel restart buttons from a config entry."""
    coordinator: DiscoPanelDataUpdateCoordinator = hass.data[DOMAIN][
        entry.entry_id
    ]

    known: set[str] = set()

    @callback
    def _add_new_entities() -> None:
        """Add button entities for any newly discovered servers."""
        new_entities: list[DiscoPanelRestartButton] = []
        for server_id in coordinator.data or {}:
            if server_id in known:
                continue
            known.add(server_id)
            new_entities.append(
                DiscoPanelRestartButton(coordinator, server_id)
            )
        if new_entities:
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class DiscoPanelRestartButton(DiscoPanelServerEntity, ButtonEntity):
    """A button that restarts a DiscoPanel server."""

    _attr_translation_key = "restart"
    _attr_icon = "mdi:restart"

    def __init__(
        self,
        coordinator: DiscoPanelDataUpdateCoordinator,
        server_id: str,
    ) -> None:
        """Initialize the restart button."""
        super().__init__(coordinator, server_id)
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_{server_id}_restart"
        )

    async def async_press(self) -> None:
        """Restart the server."""
        try:
            await self.coordinator.api.restart_server(self._server_id)
        except DiscoPanelError as err:
            raise HomeAssistantError(
                f"Failed to restart server {self._server_id}: {err}"
            ) from err
        await self.coordinator.async_request_refresh()
