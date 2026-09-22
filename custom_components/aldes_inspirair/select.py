"""Sélecteurs : niveau de ventilation et stratégie du bypass."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import BYPASS_MODES, REG_BYPASS_MODE, REG_SPEED, SPEEDS
from .coordinator import AldesConfigEntry, AldesCoordinator
from .entity import AldesEntity


@dataclass(frozen=True, kw_only=True)
class AldesSelectDescription(SelectEntityDescription):
    register: int
    choices: dict[int, str]


DESCRIPTIONS = (
    AldesSelectDescription(key="niveau", register=REG_SPEED, choices=SPEEDS),
    AldesSelectDescription(key="bypass_mode", register=REG_BYPASS_MODE, choices=BYPASS_MODES),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: AldesConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities(AldesSelect(entry.runtime_data, d) for d in DESCRIPTIONS)


class AldesSelect(AldesEntity, SelectEntity):
    entity_description: AldesSelectDescription

    def __init__(self, coordinator: AldesCoordinator, description: AldesSelectDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_options = list(description.choices.values())

    @property
    def current_option(self) -> str | None:
        return self.entity_description.choices.get(self.coordinator.value(self.entity_description.register))

    async def async_select_option(self, option: str) -> None:
        code = next(c for c, key in self.entity_description.choices.items() if key == option)
        await self.coordinator.async_write(self.entity_description.register, code)
