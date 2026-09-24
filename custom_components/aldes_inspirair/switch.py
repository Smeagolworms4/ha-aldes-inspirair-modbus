"""Remise à l'heure automatique de l'horloge de la VMC, désactivée par défaut."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_ON, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .coordinator import AldesConfigEntry
from .entity import AldesEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: AldesConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([AldesClockSync(entry.runtime_data, "horloge_auto")])


class AldesClockSync(AldesEntity, SwitchEntity, RestoreEntity):
    """Autorise Home Assistant à recaler l'horloge de la VMC au-delà de la tolérance.

    Désactivé par défaut : la ConnectBox recale déjà l'horloge quand elle a Internet.
    """

    _attr_entity_category = EntityCategory.CONFIG

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if last := await self.async_get_last_state():
            self.coordinator.clock_sync = last.state == STATE_ON

    @property
    def is_on(self) -> bool:
        return self.coordinator.clock_sync

    @property
    def available(self) -> bool:
        return True  # un réglage de Home Assistant reste modifiable, VMC injoignable ou non

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.clock_sync = True
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.clock_sync = False
        self.async_write_ha_state()
