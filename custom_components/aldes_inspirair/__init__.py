"""Intégration Aldes InspirAIR Top via passerelle Modbus TCP."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_SLAVE
from .coordinator import AldesConfigEntry, AldesCoordinator
from .modbus import AldesModbusClient

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.FAN,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: AldesConfigEntry) -> bool:
    client = AldesModbusClient(entry.data[CONF_HOST], entry.data[CONF_PORT], entry.data[CONF_SLAVE])
    coordinator = AldesCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AldesConfigEntry) -> bool:
    entry.runtime_data.cancel_boost()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
