"""Config flow for the DiscoPanel integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    DiscoPanelApi,
    DiscoPanelAuthError,
    DiscoPanelConnectionError,
    DiscoPanelError,
)
from .const import (
    CONF_API_TOKEN,
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SSL,
    CONF_VERIFY_SSL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


def _user_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the user-step data schema, pre-filled with defaults."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_HOST, default=defaults.get(CONF_HOST, "")
            ): str,
            vol.Required(
                CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)
            ): int,
            vol.Required(
                CONF_SSL, default=defaults.get(CONF_SSL, DEFAULT_SSL)
            ): bool,
            vol.Required(
                CONF_VERIFY_SSL,
                default=defaults.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
            ): bool,
            vol.Required(
                CONF_API_TOKEN, default=defaults.get(CONF_API_TOKEN, "")
            ): str,
        }
    )


async def _validate_input(
    hass: Any, data: dict[str, Any]
) -> None:
    """Validate the user input by probing the DiscoPanel API.

    Raises one of the API exceptions on failure.
    """
    session = async_get_clientsession(hass)
    api = DiscoPanelApi(
        session=session,
        host=data[CONF_HOST],
        port=data[CONF_PORT],
        token=data[CONF_API_TOKEN],
        use_ssl=data[CONF_SSL],
        verify_ssl=data[CONF_VERIFY_SSL],
    )

    # Reachability / auth-config probe (no auth). Raises on connect error.
    await api.get_auth_status()

    # Authenticated call. Raises DiscoPanelAuthError on 401.
    await api.list_servers(full_stats=False)


class DiscoPanelConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DiscoPanel."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input[CONF_PORT]
            user_input[CONF_HOST] = host

            unique_id = f"{host}:{port}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            try:
                await _validate_input(self.hass, user_input)
            except DiscoPanelAuthError:
                errors["base"] = "invalid_auth"
            except DiscoPanelConnectionError:
                errors["base"] = "cannot_connect"
            except DiscoPanelError:
                errors["base"] = "unknown"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating DiscoPanel")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"DiscoPanel ({host})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when the API token becomes invalid."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm re-authentication by collecting a fresh API token."""
        errors: dict[str, str] = {}
        reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        assert reauth_entry is not None

        if user_input is not None:
            data = {**reauth_entry.data, CONF_API_TOKEN: user_input[CONF_API_TOKEN]}
            try:
                await _validate_input(self.hass, data)
            except DiscoPanelAuthError:
                errors["base"] = "invalid_auth"
            except DiscoPanelConnectionError:
                errors["base"] = "cannot_connect"
            except DiscoPanelError:
                errors["base"] = "unknown"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during DiscoPanel reauth")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry, data=data
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_API_TOKEN): str}),
            description_placeholders={"host": reauth_entry.data[CONF_HOST]},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> DiscoPanelOptionsFlow:
        """Return the options flow handler."""
        return DiscoPanelOptionsFlow(config_entry)


class DiscoPanelOptionsFlow(OptionsFlow):
    """Handle DiscoPanel options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Store the config entry for backwards-compatible access."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self._config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL, default=current
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
