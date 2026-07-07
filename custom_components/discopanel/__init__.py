"""The DiscoPanel integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    DiscoPanelApi,
    DiscoPanelAuthError,
    DiscoPanelConnectionError,
    DiscoPanelError,
)
from .const import (
    ATTR_COMMAND,
    ATTR_SERVER_ID,
    ATTR_SILENT,
    CONF_API_TOKEN,
    CONF_HOST,
    CONF_PORT,
    CONF_SSL,
    CONF_VERIFY_SSL,
    DEFAULT_PORT,
    DEFAULT_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    SERVICE_SEND_COMMAND,
)
from .coordinator import DiscoPanelDataUpdateCoordinator
from .entity import DiscoPanelServerEntity

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
]

SEND_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SERVER_ID): cv.string,
        vol.Required(ATTR_COMMAND): cv.string,
        vol.Optional(ATTR_SILENT, default=True): cv.boolean,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DiscoPanel from a config entry."""
    session = async_get_clientsession(hass)
    api = DiscoPanelApi(
        session=session,
        host=entry.data[CONF_HOST],
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
        token=entry.data[CONF_API_TOKEN],
        use_ssl=entry.data.get(CONF_SSL, DEFAULT_SSL),
        verify_ssl=entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
    )

    coordinator = DiscoPanelDataUpdateCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Register the panel hub device so per-server devices can link to it via
    # ``via_device``. Without this the via_device reference would be dangling.
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        **DiscoPanelServerEntity.hub_device_info(entry.entry_id, api.base_url),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _async_register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN, None)
            _async_unregister_services(hass)
    return unload_ok


async def _async_update_listener(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Reload the config entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


def _find_coordinator_for_server(
    hass: HomeAssistant, server_id: str
) -> DiscoPanelDataUpdateCoordinator | None:
    """Return the coordinator that currently knows about ``server_id``."""
    for coordinator in hass.data.get(DOMAIN, {}).values():
        if isinstance(coordinator, DiscoPanelDataUpdateCoordinator):
            if server_id in (coordinator.data or {}):
                return coordinator
    # Fall back to any single coordinator if only one entry is configured.
    coordinators = [
        c
        for c in hass.data.get(DOMAIN, {}).values()
        if isinstance(c, DiscoPanelDataUpdateCoordinator)
    ]
    if len(coordinators) == 1:
        return coordinators[0]
    return None


def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services (idempotent)."""
    if hass.services.has_service(DOMAIN, SERVICE_SEND_COMMAND):
        return

    async def _handle_send_command(call: ServiceCall) -> ServiceResponse:
        server_id: str = call.data[ATTR_SERVER_ID]
        command: str = call.data[ATTR_COMMAND]
        silent: bool = call.data[ATTR_SILENT]

        coordinator = _find_coordinator_for_server(hass, server_id)
        if coordinator is None:
            raise HomeAssistantError(
                f"No DiscoPanel server found with id '{server_id}'"
            )

        try:
            result = await coordinator.api.send_command(
                server_id, command, silent
            )
        except DiscoPanelAuthError as err:
            raise HomeAssistantError(f"Authentication failed: {err}") from err
        except DiscoPanelConnectionError as err:
            raise HomeAssistantError(f"Connection error: {err}") from err
        except DiscoPanelError as err:
            raise HomeAssistantError(f"Command failed: {err}") from err

        # The call can succeed at the HTTP level but be rejected logically.
        if result.get("success") is False:
            raise HomeAssistantError(
                result.get("error") or "Command was rejected by the server"
            )

        await coordinator.async_request_refresh()

        return {
            "success": bool(result.get("success", True)),
            "output": result.get("output", ""),
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_COMMAND,
        _handle_send_command,
        schema=SEND_COMMAND_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )


def _async_unregister_services(hass: HomeAssistant) -> None:
    """Remove integration services when the last entry is unloaded."""
    if hass.services.has_service(DOMAIN, SERVICE_SEND_COMMAND):
        hass.services.async_remove(DOMAIN, SERVICE_SEND_COMMAND)
