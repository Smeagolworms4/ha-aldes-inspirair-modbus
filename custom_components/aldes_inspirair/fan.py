"""La VMC en entité ventilateur : 4 niveaux, pas d'arrêt possible."""

from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.percentage import ordered_list_item_to_percentage, percentage_to_ordered_list_item

from .const import AUTO, LEVELS, REG_APPLIED_LEVEL, REG_SPEED, SPEEDS
from .coordinator import AldesConfigEntry
from .entity import AldesEntity

ORDERED = list(LEVELS.values())          # du plus faible au plus fort, pour le pourcentage
PRESETS = [*ORDERED, SPEEDS[AUTO]]
BY_KEY = {key: code for code, key in SPEEDS.items()}


async def async_setup_entry(
    hass: HomeAssistant, entry: AldesConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([AldesFan(entry.runtime_data, "ventilation")])


class AldesFan(AldesEntity, FanEntity):
    _attr_name = None
    _attr_preset_modes = PRESETS
    _attr_speed_count = len(ORDERED)
    _attr_supported_features = FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE | FanEntityFeature.TURN_ON

    @property
    def _speed(self) -> str | None:
        """Le mode choisi : un niveau, ou « auto »."""
        return SPEEDS.get(self.coordinator.value(REG_SPEED))

    @property
    def _applied(self) -> str | None:
        """Le niveau que la VMC applique réellement — le seul lisible en mode auto."""
        return LEVELS.get(self.coordinator.value(REG_APPLIED_LEVEL))

    @property
    def is_on(self) -> bool | None:
        # Une VMC double flux ne s'arrête pas : « vacances » est le niveau le plus bas.
        return None if self._speed is None else True

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        return {"applied_level": self._applied}

    @property
    def preset_mode(self) -> str | None:
        return self._speed

    @property
    def percentage(self) -> int | None:
        applied = self._applied
        return ordered_list_item_to_percentage(ORDERED, applied) if applied else None

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self.coordinator.async_write(REG_SPEED, BY_KEY[preset_mode])

    async def async_set_percentage(self, percentage: int) -> None:
        key = ORDERED[0] if percentage == 0 else percentage_to_ordered_list_item(ORDERED, percentage)
        await self.async_set_preset_mode(key)

    async def async_turn_on(
        self, percentage: int | None = None, preset_mode: str | None = None, **kwargs: Any
    ) -> None:
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
        elif percentage is not None:
            await self.async_set_percentage(percentage)
