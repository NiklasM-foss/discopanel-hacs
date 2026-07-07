"""Binary sensor platform for the DiscoPanel integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, is_running
from .coordinator import DiscoPanelDataUpdateCoordinator
from .entity import DiscoPanelServerEntity


@dataclass(frozen=True, kw_only=True)
class DiscoPanelBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a DiscoPanel binary sensor entity."""

    value_fn: Callable[[dict[str, Any]], bool]


BINARY_SENSOR_DESCRIPTIONS: tuple[
    DiscoPanelBinarySensorEntityDescription, ...
] = (
    DiscoPanelBinarySensorEntityDescription(
        key="running",
        translation_key="running",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda server: is_running(server.get("status")),
    ),
    DiscoPanelBinarySensorEntityDescription(
        key="reachable",
        translation_key="reachable",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda server: bool(server.get("slpAvailable")),
    ),
    DiscoPanelBinarySensorEntityDescription(
        key="auto_start",
        translation_key="auto_start",
        icon="mdi:restart-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda server: bool(server.get("autoStart")),
    ),
    DiscoPanelBinarySensorEntityDescription(
        key="detached",
        translation_key="detached",
        icon="mdi:transit-connection-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda server: bool(server.get("detached")),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DiscoPanel binary sensors from a config entry."""
    coordinator: DiscoPanelDataUpdateCoordinator = hass.data[DOMAIN][
        entry.entry_id
    ]

    known: set[str] = set()

    @callback
    def _add_new_entities() -> None:
        """Add binary sensor entities for any newly discovered servers."""
        new_entities: list[DiscoPanelBinarySensor] = []
        for server_id in coordinator.data or {}:
            if server_id in known:
                continue
            known.add(server_id)
            for description in BINARY_SENSOR_DESCRIPTIONS:
                new_entities.append(
                    DiscoPanelBinarySensor(coordinator, server_id, description)
                )
        if new_entities:
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class DiscoPanelBinarySensor(DiscoPanelServerEntity, BinarySensorEntity):
    """A single DiscoPanel server binary sensor."""

    entity_description: DiscoPanelBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: DiscoPanelDataUpdateCoordinator,
        server_id: str,
        description: DiscoPanelBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, server_id)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_{server_id}_{description.key}"
        )

    @property
    def is_on(self) -> bool:
        """Return True if the binary sensor is on."""
        return self.entity_description.value_fn(self.server)
