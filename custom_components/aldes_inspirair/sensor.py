"""Capteurs : températures, débits, filtres, bypass, erreurs, moteurs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    BYPASS_POSITIONS,
    LEVELS,
    ERROR_CODES,
    ERROR_UNKNOWN,
    REG_BALANCE,
    REG_BYPASS_POSITION,
    REG_ERROR,
    REG_APPLIED_LEVEL,
    REG_FILTER_SINCE_RESET,
    REG_FILTER_USE,
    REG_FLOW_EXTRACT,
    REG_FLOW_SUPPLY,
    REG_MOTOR_CMD_1,
    REG_MOTOR_CMD_2,
    REG_MOTOR_RPM_1,
    REG_MOTOR_RPM_2,
    REG_T_EXHAUST,
    REG_T_EXTRACT,
    REG_T_OUTDOOR,
    REG_T_SUPPLY,
    error_key,
)
from .coordinator import AldesConfigEntry, AldesCoordinator
from .entity import AldesEntity


@dataclass(frozen=True, kw_only=True)
class AldesSensorDescription(SensorEntityDescription):
    value_fn: Callable[[AldesCoordinator], float | int | str | None]


def reg(register: int, scale: float = 1.0) -> Callable[[AldesCoordinator], float | int | None]:
    def _read(c: AldesCoordinator) -> float | int | None:
        raw = c.value(register)
        if raw is None:
            return None
        return round(raw * scale, 3) if scale != 1.0 else raw

    return _read


def temperature(key: str, register: int) -> AldesSensorDescription:
    return AldesSensorDescription(
        key=key,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=reg(register, 0.01),
    )


def flow(key: str, register: int) -> AldesSensorDescription:
    return AldesSensorDescription(
        key=key,
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        value_fn=reg(register),
    )


def motor_command(key: str, register: int) -> AldesSensorDescription:
    return AldesSensorDescription(
        key=key,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=reg(register, 0.001),
    )


def motor_speed(key: str, register: int) -> AldesSensorDescription:
    return AldesSensorDescription(
        key=key,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=reg(register),
    )


def exchanger_efficiency(c: AldesCoordinator) -> float | None:
    """Rendement de l'échangeur, uniquement quand l'air le traverse (bypass fermé)."""
    if c.value(REG_BYPASS_POSITION) != 0:
        return None
    outdoor, extract, supply = (c.value(r) for r in (REG_T_OUTDOOR, REG_T_EXTRACT, REG_T_SUPPLY))
    if outdoor is None or extract is None or supply is None or abs(extract - outdoor) < 300:
        return None  # écart intérieur/extérieur < 3 °C : calcul non significatif
    return round(100 * (supply - outdoor) / (extract - outdoor), 1)


def error_state(c: AldesCoordinator) -> str | None:
    code = c.value(REG_ERROR)
    return None if code is None else error_key(code)


DESCRIPTIONS = (
    temperature("temp_exterieure", REG_T_OUTDOOR),
    temperature("temp_extraite", REG_T_EXTRACT),
    temperature("temp_rejetee", REG_T_EXHAUST),
    temperature("temp_insufflee", REG_T_SUPPLY),
    flow("debit_extraction", REG_FLOW_EXTRACT),
    flow("debit_insufflation", REG_FLOW_SUPPLY),
    AldesSensorDescription(
        key="rendement_echangeur",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=exchanger_efficiency,
    ),
    AldesSensorDescription(
        key="niveau_en_cours",
        device_class=SensorDeviceClass.ENUM,
        options=list(LEVELS.values()),
        value_fn=lambda c: LEVELS.get(c.value(REG_APPLIED_LEVEL)),
    ),
    AldesSensorDescription(
        key="filtres_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=reg(REG_FILTER_USE),
    ),
    AldesSensorDescription(
        key="filtres_depuis_reset",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        value_fn=reg(REG_FILTER_SINCE_RESET),
    ),
    AldesSensorDescription(
        key="bypass_position",
        device_class=SensorDeviceClass.ENUM,
        options=list(BYPASS_POSITIONS.values()),
        value_fn=lambda c: BYPASS_POSITIONS.get(c.value(REG_BYPASS_POSITION)),
    ),
    AldesSensorDescription(
        key="erreur",
        device_class=SensorDeviceClass.ENUM,
        options=[error_key(code) for code in ERROR_CODES] + [ERROR_UNKNOWN],
        value_fn=error_state,
    ),
    AldesSensorDescription(
        key="code_erreur",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=reg(REG_ERROR),
    ),
    AldesSensorDescription(
        key="equilibrage",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=reg(REG_BALANCE),
    ),
    motor_command("commande_moteur_extraction", REG_MOTOR_CMD_1),
    motor_command("commande_moteur_insufflation", REG_MOTOR_CMD_2),
    motor_speed("regime_moteur_extraction", REG_MOTOR_RPM_1),
    motor_speed("regime_moteur_insufflation", REG_MOTOR_RPM_2),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: AldesConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities(AldesSensor(entry.runtime_data, d) for d in DESCRIPTIONS)


class AldesSensor(AldesEntity, SensorEntity):
    entity_description: AldesSensorDescription

    def __init__(self, coordinator: AldesCoordinator, description: AldesSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | str | None:
        return self.entity_description.value_fn(self.coordinator)
