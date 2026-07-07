"""Sensor platform for the DiscoPanel integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfInformation,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    SERVER_STATUS_OPTIONS,
    normalize_status,
)
from .coordinator import DiscoPanelDataUpdateCoordinator
from .entity import DiscoPanelServerEntity


@dataclass(frozen=True, kw_only=True)
class DiscoPanelSensorEntityDescription(SensorEntityDescription):
    """Describes a DiscoPanel sensor entity."""

    value_fn: Callable[[dict[str, Any]], Any]
    attr_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def _players_online(server: dict[str, Any]) -> int:
    return int(server.get("playersOnline") or 0)


def _players_attrs(server: dict[str, Any]) -> dict[str, Any]:
    attrs: dict[str, Any] = {
        "max_players": server.get("maxPlayers"),
    }
    sample = server.get("playerSample")
    if isinstance(sample, list):
        attrs["player_sample"] = sample
    return attrs


def _int_or_none(server: dict[str, Any], key: str) -> int | None:
    value = server.get(key)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_none(server: dict[str, Any], key: str) -> float | None:
    value = server.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _str_or_none(server: dict[str, Any], key: str) -> str | None:
    value = server.get(key)
    if value is None:
        return None
    text = str(value)
    return text or None


SENSOR_DESCRIPTIONS: tuple[DiscoPanelSensorEntityDescription, ...] = (
    DiscoPanelSensorEntityDescription(
        key="status",
        translation_key="status",
        icon="mdi:minecraft",
        device_class=SensorDeviceClass.ENUM,
        options=SERVER_STATUS_OPTIONS,
        value_fn=lambda server: normalize_status(server.get("status")),
        attr_fn=lambda server: {"raw_status": server.get("status")},
    ),
    DiscoPanelSensorEntityDescription(
        key="players_online",
        translation_key="players_online",
        icon="mdi:account-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_players_online,
        attr_fn=_players_attrs,
    ),
    DiscoPanelSensorEntityDescription(
        key="tps",
        translation_key="tps",
        icon="mdi:speedometer",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda server: _float_or_none(server, "tps"),
    ),
    DiscoPanelSensorEntityDescription(
        key="cpu_percent",
        translation_key="cpu_percent",
        icon="mdi:cpu-64-bit",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda server: _float_or_none(server, "cpuPercent"),
    ),
    DiscoPanelSensorEntityDescription(
        # DiscoPanel reports memoryUsage already in MB (client.go: float64 MB,
        # emitted as int64 MB), unlike the disk fields which are raw bytes.
        key="memory_usage",
        translation_key="memory_usage",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        suggested_display_precision=1,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda server: _int_or_none(server, "memoryUsage"),
    ),
    DiscoPanelSensorEntityDescription(
        key="disk_usage",
        translation_key="disk_usage",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda server: _int_or_none(server, "diskUsage"),
        attr_fn=lambda server: {"disk_total": _int_or_none(server, "diskTotal")},
    ),
    DiscoPanelSensorEntityDescription(
        key="world_size",
        translation_key="world_size",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda server: _int_or_none(server, "worldSize"),
    ),
    DiscoPanelSensorEntityDescription(
        key="latency",
        translation_key="latency",
        icon="mdi:timer-outline",
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda server: _int_or_none(server, "slpLatencyMs"),
    ),
    DiscoPanelSensorEntityDescription(
        key="mc_version",
        translation_key="mc_version",
        icon="mdi:tag-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda server: _str_or_none(server, "mcVersion"),
    ),
    DiscoPanelSensorEntityDescription(
        key="motd",
        translation_key="motd",
        icon="mdi:message-text-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda server: _str_or_none(server, "motd"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DiscoPanel sensors from a config entry."""
    coordinator: DiscoPanelDataUpdateCoordinator = hass.data[DOMAIN][
        entry.entry_id
    ]

    known: set[str] = set()

    @callback
    def _add_new_entities() -> None:
        """Add sensor entities for any newly discovered servers."""
        new_entities: list[DiscoPanelSensor] = []
        for server_id in coordinator.data or {}:
            if server_id in known:
                continue
            known.add(server_id)
            for description in SENSOR_DESCRIPTIONS:
                new_entities.append(
                    DiscoPanelSensor(coordinator, server_id, description)
                )
        if new_entities:
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class DiscoPanelSensor(DiscoPanelServerEntity, SensorEntity):
    """A single DiscoPanel server sensor."""

    entity_description: DiscoPanelSensorEntityDescription

    def __init__(
        self,
        coordinator: DiscoPanelDataUpdateCoordinator,
        server_id: str,
        description: DiscoPanelSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, server_id)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_{server_id}_{description.key}"
        )

    @property
    def native_value(self) -> Any:
        """Return the current sensor value."""
        return self.entity_description.value_fn(self.server)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes, if any."""
        if self.entity_description.attr_fn is None:
            return None
        return self.entity_description.attr_fn(self.server)
