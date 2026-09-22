"""Durée de vie des filtres (6 à 12 mois, comme dans le menu de la télécommande)."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import REG_FILTER_MONTHS
from .coordinator import AldesConfigEntry
from .entity import AldesEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: AldesConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([AldesFilterDuration(entry.runtime_data, "filtre_duree")])


class AldesFilterDuration(AldesEntity, NumberEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 6
    _attr_native_max_value = 12
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MONTHS
    _attr_mode = NumberMode.BOX

    @property
    def native_value(self) -> int | None:
        return self.coordinator.value(REG_FILTER_MONTHS)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_write(REG_FILTER_MONTHS, int(value))
