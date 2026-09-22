"""Assistant de configuration : passerelle, esclave Modbus, intervalle d'interrogation."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlowWithReload
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback

from .const import (
    CONF_SCAN_INTERVAL,
    CONF_SLAVE,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    REG_SPEED,
)
from .modbus import AldesModbusClient, AldesModbusError


def _connection_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, DEFAULT_HOST)): str,
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=65535)
            ),
            vol.Required(CONF_SLAVE, default=defaults.get(CONF_SLAVE, DEFAULT_SLAVE)): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=247)
            ),
        }
    )


async def _probe(data: dict[str, Any]) -> bool:
    """Vrai si la VMC répond via cette passerelle."""
    try:
        await AldesModbusClient(data[CONF_HOST], data[CONF_PORT], data[CONF_SLAVE]).read(REG_SPEED, 1)
    except AldesModbusError:
        return False
    return True


class AldesConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> AldesOptionsFlow:
        return AldesOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(f"{user_input[CONF_HOST]}:{user_input[CONF_SLAVE]}")
            self._abort_if_unique_id_configured()
            if await _probe(user_input):
                return self.async_create_entry(title="VMC Aldes", data=user_input)
            errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="user", data_schema=_connection_schema(user_input or {}), errors=errors
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            # L'identifiant unique reste celui d'origine : changer d'IP ne doit pas recréer les entités.
            if await _probe(user_input):
                return self.async_update_reload_and_abort(entry, data=user_input)
            errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="reconfigure", data_schema=_connection_schema(user_input or dict(entry.data)), errors=errors
        )


class AldesOptionsFlow(OptionsFlowWithReload):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                    vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
