"""Entité de base rattachée au device VMC."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, REG_SOFTWARE
from .coordinator import AldesCoordinator


class AldesEntity(CoordinatorEntity[AldesCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: AldesCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.unique_id}_{key}"
        self._attr_translation_key = key
        software = coordinator.value(REG_SOFTWARE)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name="VMC Aldes",
            manufacturer="Aldes",
            model="InspirAIR Top",
            sw_version=str(software) if software is not None else None,
            configuration_url=f"http://{coordinator.client.host}",
        )
