"""Rafraîchissement périodique des registres de la VMC."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, READ_BLOCKS
from .modbus import AldesModbusClient, AldesModbusError

_LOGGER = logging.getLogger(__name__)

type AldesConfigEntry = ConfigEntry[AldesCoordinator]


class AldesCoordinator(DataUpdateCoordinator[dict[int, int]]):
    """Lit les blocs de registres et centralise les écritures."""

    def __init__(self, hass: HomeAssistant, entry: AldesConfigEntry, client: AldesModbusClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
        )
        self.client = client

    async def _async_update_data(self) -> dict[int, int]:
        data: dict[int, int] = {}
        try:
            # Le déverrouillage part avant chaque lecture : on ne sait pas combien de temps il tient.
            await self.client.unlock()
            for start, count in READ_BLOCKS:
                for offset, value in enumerate(await self.client.read(start, count)):
                    data[start + offset] = value
        except AldesModbusError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN, translation_key="update_failed", translation_placeholders={"error": str(err)}
            ) from err
        return data

    def value(self, register: int) -> int | None:
        """Valeur brute, ou None si absente ou verrouillée (-1)."""
        if not self.data:
            return None
        value = self.data.get(register)
        return None if value in (None, -1) else value

    async def async_write(self, register: int, value: int) -> None:
        try:
            await self.client.unlock()
            await self.client.write(register, value)
        except AldesModbusError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
                translation_placeholders={"register": str(register), "error": str(err)},
            ) from err
        self.data[register] = value
        self.async_update_listeners()
        await self.async_request_refresh()
