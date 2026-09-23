"""Réglages numériques : durée de vie des filtres, et durée du boost tenue par Home Assistant."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode, RestoreNumber
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import MAX_BOOST_MINUTES, REG_FILTER_MONTHS
from .coordinator import AldesConfigEntry
from .entity import AldesEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: AldesConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [AldesFilterDuration(coordinator, "filtre_duree"), AldesBoostDuration(coordinator, "boost_duree")]
    )


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


class AldesBoostDuration(AldesEntity, RestoreNumber):
    """L'InspirAIR Top n'a pas de temporisation de boost : celle-ci vit dans Home Assistant.

    Elle s'applique aux boosts demandés depuis Home Assistant. Un boost lancé depuis la
    télécommande reste actif jusqu'à ce que quelqu'un change de niveau.
    """

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0
    _attr_native_max_value = MAX_BOOST_MINUTES
    _attr_native_step = 5
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.BOX

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_number_data()) and last.native_value is not None:
            self.coordinator.boost_minutes = last.native_value

    @property
    def native_value(self) -> float:
        return self.coordinator.boost_minutes

    @property
    def available(self) -> bool:
        return True  # un réglage de Home Assistant reste modifiable, VMC injoignable ou non

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.boost_minutes = value
        if not value:
            self.coordinator.cancel_boost()  # 0 = boost permanent
        self.async_write_ha_state()
