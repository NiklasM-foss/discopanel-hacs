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
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    SERVER_STATUS_OPTIONS,
    is_running,
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


def _dt_or_none(server: dict[str, Any], key: str) -> Any:
    """Parse an RFC3339 timestamp field into an aware datetime, or None.

    DiscoPanel emits a zero timestamp (0001-01-01T...) for never-set values;
    treat anything before year 2000 as unset.
    """
    value = server.get(key)
    if not value:
        return None
    parsed = dt_util.parse_datetime(str(value))
    if parsed is None or parsed.year < 2000:
        return None
    return parsed


SENSOR_DESCRIPTIONS: tuple[DiscoPanelSensorEntityDescription, ...] = (
    DiscoPanelSensorEntityDescription(
        key="status",
        translation_key="status",
        icon="mdi:minecraft",
        device_class=SensorDeviceClass.ENUM,
        options=SERVER_STATUS_OPTIONS,
        value_fn=lambda server: normalize_status(server.get("status")),
        attr_fn=lambda server: {
            "raw_status": server.get("status"),
            "updated_at": server.get("updatedAt"),
            "additional_ports": server.get("additionalPorts"),
        },
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
        attr_fn=lambda server: {"tps_command": _str_or_none(server, "tpsCommand")},
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
    # --- Configuration / capacity ---------------------------------------
    DiscoPanelSensorEntityDescription(
        key="memory_configured",
        translation_key="memory_configured",
        icon="mdi:memory",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda server: _int_or_none(server, "memory"),
    ),
    DiscoPanelSensorEntityDescription(
        key="max_players",
        translation_key="max_players",
        icon="mdi:account-multiple-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda server: _int_or_none(server, "maxPlayers"),
    ),
    DiscoPanelSensorEntityDescription(
        key="disk_total",
        translation_key="disk_total",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda server: _int_or_none(server, "diskTotal"),
    ),
    DiscoPanelSensorEntityDescription(
        key="port",
        translation_key="port",
        icon="mdi:lan",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda server: _int_or_none(server, "port"),
    ),
    DiscoPanelSensorEntityDescription(
        key="proxy_port",
        translation_key="proxy_port",
        icon="mdi:lan-connect",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda server: _int_or_none(server, "proxyPort"),
        attr_fn=lambda server: {
            "proxy_hostname": _str_or_none(server, "proxyHostname"),
            "proxy_listener_id": _str_or_none(server, "proxyListenerId"),
        },
    ),
    # --- Runtime / container --------------------------------------------
    DiscoPanelSensorEntityDescription(
        key="java_version",
        translation_key="java_version",
        icon="mdi:language-java",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda server: _int_or_none(server, "javaVersion"),
    ),
    DiscoPanelSensorEntityDescription(
        key="docker_image",
        translation_key="docker_image",
        icon="mdi:docker",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda server: _str_or_none(server, "dockerImage"),
    ),
    DiscoPanelSensorEntityDescription(
        key="container_id",
        translation_key="container_id",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda server: (_str_or_none(server, "containerId") or "")[:12]
        or None,
        attr_fn=lambda server: {
            "full_container_id": _str_or_none(server, "containerId"),
            "data_path": _str_or_none(server, "dataPath"),
        },
    ),
    DiscoPanelSensorEntityDescription(
        key="last_started",
        translation_key="last_started",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda server: _dt_or_none(server, "lastStarted"),
    ),
    DiscoPanelSensorEntityDescription(
        key="created_at",
        translation_key="created_at",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda server: _dt_or_none(server, "createdAt"),
    ),
    # --- Server List Ping (only meaningful while running) ---------------
    DiscoPanelSensorEntityDescription(
        key="server_version",
        translation_key="server_version",
        icon="mdi:server",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda server: _str_or_none(server, "serverVersion"),
    ),
    DiscoPanelSensorEntityDescription(
        key="protocol_version",
        translation_key="protocol_version",
        icon="mdi:protocol",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda server: _int_or_none(server, "protocolVersion"),
    ),
    DiscoPanelSensorEntityDescription(
        key="max_players_slp",
        translation_key="max_players_slp",
        icon="mdi:account-multiple-outline",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda server: _int_or_none(server, "maxPlayersSlp"),
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

    # Panel-wide sensor on the hub device (added once, not per server).
    async_add_entities([DiscoPanelTotalPlayersSensor(coordinator)])

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


class DiscoPanelTotalPlayersSensor(
    CoordinatorEntity[DiscoPanelDataUpdateCoordinator], SensorEntity
):
    """Total number of players online across all servers on the panel."""

    _attr_has_entity_name = True
    _attr_translation_key = "total_players"
    _attr_icon = "mdi:account-group"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: DiscoPanelDataUpdateCoordinator) -> None:
        """Initialize the panel-wide total-players sensor."""
        super().__init__(coordinator)
        entry_id = coordinator.entry.entry_id
        self._attr_unique_id = f"{entry_id}_total_players"
        # Attach to the panel hub device (created in async_setup_entry).
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def available(self) -> bool:
        """Return True while the coordinator is updating successfully."""
        return self.coordinator.last_update_success

    @property
    def native_value(self) -> int:
        """Return the summed player count across all known servers."""
        return sum(
            int(server.get("playersOnline") or 0)
            for server in (self.coordinator.data or {}).values()
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return per-server breakdown and running/total server counts."""
        data = self.coordinator.data or {}
        return {
            "max_players": sum(
                int(server.get("maxPlayers") or 0) for server in data.values()
            ),
            "servers_total": len(data),
            "servers_running": sum(
                1 for server in data.values() if is_running(server.get("status"))
            ),
            "players_per_server": {
                (server.get("name") or server_id): int(
                    server.get("playersOnline") or 0
                )
                for server_id, server in data.items()
            },
        }
