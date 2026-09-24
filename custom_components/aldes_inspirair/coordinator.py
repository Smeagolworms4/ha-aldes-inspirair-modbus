"""Rafraîchissement périodique des registres de la VMC."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    BOOST,
    CLOCK_SYNC_COOLDOWN,
    CONF_SCAN_INTERVAL,
    DAILY,
    DEFAULT_BOOST_MINUTES,
    DEFAULT_CLOCK_TOLERANCE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    READ_ATTEMPTS,
    READ_BLOCKS,
    REG_CLOCK,
    REG_SPEED,
    RETRY_DELAY,
)
from .modbus import AldesModbusClient, AldesModbusError

_LOGGER = logging.getLogger(__name__)

type AldesConfigEntry = ConfigEntry[AldesCoordinator]


def unit_clock(data: dict[int, int]) -> datetime | None:
    """Horloge interne de la VMC, celle qui sert de base à la programmation horaire."""
    year, month, day, _weekday, hour, minute, second = (data.get(REG_CLOCK + i) or 0 for i in range(7))
    try:
        return datetime(year, month, day, hour, minute, second)
    except ValueError:
        return None


def clock_drift(clock: datetime, now: datetime) -> float:
    """Retard (positif) ou avance de l'horloge de la VMC sur l'heure locale, en minutes."""
    return (now.replace(tzinfo=None) - clock).total_seconds() / 60


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
        self.boost_minutes: float = DEFAULT_BOOST_MINUTES
        self._end_boost_unsub: CALLBACK_TYPE | None = None
        self._level_before_boost = DAILY
        self.clock_sync = False
        self.clock_tolerance: float = DEFAULT_CLOCK_TOLERANCE
        self._last_clock_sync: datetime | None = None

    async def _async_update_data(self) -> dict[int, int]:
        for attempt in range(1, READ_ATTEMPTS + 1):
            try:
                data = await self._read_all()
            except AldesModbusError as err:
                if attempt == READ_ATTEMPTS:
                    raise UpdateFailed(
                        translation_domain=DOMAIN,
                        translation_key="update_failed",
                        translation_placeholders={"error": str(err)},
                    ) from err
                _LOGGER.debug("Relevé %s/%s échoué (%s), nouvel essai", attempt, READ_ATTEMPTS, err)
                await asyncio.sleep(RETRY_DELAY)
            else:
                await self._sync_clock(data)
                return data
        raise AssertionError  # inatteignable

    async def _sync_clock(self, data: dict[int, int]) -> None:
        """Remet l'horloge de la VMC à l'heure locale si elle s'en écarte trop."""
        if not self.clock_sync:
            return
        clock = unit_clock(data)
        now = dt_util.now()
        if clock is None or abs(clock_drift(clock, now)) <= self.clock_tolerance:
            return
        if self._last_clock_sync and (now - self._last_clock_sync).total_seconds() < CLOCK_SYNC_COOLDOWN:
            return
        self._last_clock_sync = now
        values = [now.year, now.month, now.day, now.weekday(), now.hour, now.minute, now.second]
        _LOGGER.info("Horloge de la VMC décalée de %s min, remise à l'heure", round(clock_drift(clock, now)))
        try:
            await self.client.unlock()
            await self.client.write_many(REG_CLOCK, values)
        except AldesModbusError as err:
            _LOGGER.warning("Remise à l'heure de la VMC impossible : %s", err)
            return
        data.update({REG_CLOCK + offset: value for offset, value in enumerate(values)})

    async def _read_all(self) -> dict[int, int]:
        data: dict[int, int] = {}
        # Le déverrouillage part avant chaque lecture : on ne sait pas combien de temps il tient.
        await self.client.unlock()
        for start, count in READ_BLOCKS:
            for offset, value in enumerate(await self.client.read(start, count)):
                data[start + offset] = value
        return data

    def value(self, register: int) -> int | None:
        """Valeur brute, ou None si absente ou verrouillée (-1)."""
        if not self.data:
            return None
        value = self.data.get(register)
        return None if value in (None, -1) else value

    async def async_set_speed(self, code: int) -> None:
        """Change de niveau, et arme la temporisation quand c'est un boost."""
        previous = self.value(REG_SPEED)
        self.cancel_boost()
        await self.async_write(REG_SPEED, code)
        if code == BOOST and self.boost_minutes:
            self._level_before_boost = DAILY if previous in (None, BOOST) else previous
            self._end_boost_unsub = async_call_later(self.hass, self.boost_minutes * 60, self._end_boost)

    async def _end_boost(self, _now) -> None:
        self._end_boost_unsub = None
        # Quelqu'un a pu reprendre la main entre-temps, depuis la télécommande par exemple.
        if self.value(REG_SPEED) == BOOST:
            await self.async_write(REG_SPEED, self._level_before_boost)

    def cancel_boost(self) -> None:
        if self._end_boost_unsub is not None:
            self._end_boost_unsub()
            self._end_boost_unsub = None

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
