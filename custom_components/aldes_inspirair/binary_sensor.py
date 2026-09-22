"""Capteurs binaires : bypass ouvert, défaut en cours."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import REG_BYPASS_POSITION, REG_ERROR
from .coordinator import AldesConfigEntry
from .entity import AldesEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: AldesConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([AldesBypassOpen(coordinator, "bypass_ouvert"), AldesProblem(coordinator, "defaut")])


class AldesBypassOpen(AldesEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.OPENING

    @property
    def is_on(self) -> bool | None:
        position = self.coordinator.value(REG_BYPASS_POSITION)
        return None if position is None else position in (1, 3)


class AldesProblem(AldesEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool | None:
        code = self.coordinator.value(REG_ERROR)
        return None if code is None else code != 0

    @property
    def extra_state_attributes(self) -> dict[str, int | None]:
        return {"code": self.coordinator.value(REG_ERROR)}
