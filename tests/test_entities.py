"""Chaque entité du device, lue et pilotée contre la fausse VMC."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from datetime import timedelta

from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr

from custom_components.aldes_inspirair.const import DOMAIN

from .fake_vmc import FakeVmc


async def refresh(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


def state(hass: HomeAssistant, entity_id: str) -> str:
    return hass.states.get(entity_id).state


async def test_device(hass: HomeAssistant, setup_entry: MockConfigEntry) -> None:
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "127.0.0.1:2")})
    assert device.manufacturer == "Aldes"
    assert device.model == "InspirAIR Top"
    assert device.sw_version == "291"


async def test_temperatures_and_flows(hass: HomeAssistant, entity_id) -> None:
    """Les registres protégés sont lus : l'intégration déverrouille avant chaque relevé."""
    assert state(hass, entity_id("sensor", "temp_exterieure")) == "26.04"
    assert state(hass, entity_id("sensor", "temp_extraite")) == "27.32"
    assert state(hass, entity_id("sensor", "temp_rejetee")) == "27.95"
    assert state(hass, entity_id("sensor", "temp_insufflee")) == "26.31"
    assert state(hass, entity_id("sensor", "debit_extraction")) == "120"
    assert state(hass, entity_id("sensor", "debit_insufflation")) == "120"


async def test_diagnostics(hass: HomeAssistant, entity_id) -> None:
    assert state(hass, entity_id("sensor", "commande_moteur_extraction")) == "3.0"
    assert state(hass, entity_id("sensor", "commande_moteur_insufflation")) == "3.35"
    assert state(hass, entity_id("sensor", "regime_moteur_extraction")) == "1241"
    assert state(hass, entity_id("sensor", "equilibrage")) == "100"
    assert state(hass, entity_id("sensor", "filtres_usage")) == "2"
    assert state(hass, entity_id("sensor", "filtres_depuis_reset")) == "125"  # heures


async def test_bypass_open(hass: HomeAssistant, entity_id) -> None:
    assert state(hass, entity_id("sensor", "bypass_position")) == "ouvert"
    assert state(hass, entity_id("binary_sensor", "bypass_ouvert")) == "on"
    # L'air ne traverse pas l'échangeur : pas de rendement à calculer.
    assert state(hass, entity_id("sensor", "rendement_echangeur")) == STATE_UNKNOWN


async def test_exchanger_efficiency_when_bypass_closed(
    hass: HomeAssistant, setup_entry: MockConfigEntry, vmc: FakeVmc, entity_id
) -> None:
    vmc.registers.update({348: 0, 350: 500, 351: 2000, 353: 1700})
    await refresh(hass, setup_entry)

    assert state(hass, entity_id("binary_sensor", "bypass_ouvert")) == "off"
    assert state(hass, entity_id("sensor", "rendement_echangeur")) == "80.0"


async def test_efficiency_needs_a_real_temperature_gap(
    hass: HomeAssistant, setup_entry: MockConfigEntry, vmc: FakeVmc, entity_id
) -> None:
    vmc.registers.update({348: 0, 350: 2500, 351: 2600, 353: 2550})
    await refresh(hass, setup_entry)
    assert state(hass, entity_id("sensor", "rendement_echangeur")) == STATE_UNKNOWN


@pytest.mark.parametrize(("code", "expected", "problem"), [(0, "aucune", "off"), (240, "e240", "on"), (999, "inconnue", "on")])
async def test_errors(
    hass: HomeAssistant, setup_entry: MockConfigEntry, vmc: FakeVmc, entity_id, code: int, expected: str, problem: str
) -> None:
    vmc.registers[384] = code
    await refresh(hass, setup_entry)

    assert state(hass, entity_id("sensor", "erreur")) == expected
    assert state(hass, entity_id("sensor", "code_erreur")) == str(code)
    assert state(hass, entity_id("binary_sensor", "defaut")) == problem
    assert hass.states.get(entity_id("binary_sensor", "defaut")).attributes["code"] == code


async def test_fan_reflects_the_level(hass: HomeAssistant, entity_id) -> None:
    fan = hass.states.get(entity_id("fan", "ventilation"))
    assert fan.state == "on"
    assert fan.attributes["preset_mode"] == "quotidien"
    assert fan.attributes["percentage"] == 50
    assert fan.attributes["preset_modes"] == ["vacances", "quotidien", "cuisine", "boost", "auto"]
    assert fan.attributes["applied_level"] == "quotidien"


async def test_fan_preset_mode(hass: HomeAssistant, vmc: FakeVmc, entity_id) -> None:
    fan = entity_id("fan", "ventilation")
    await hass.services.async_call("fan", "set_preset_mode", {ATTR_ENTITY_ID: fan, "preset_mode": "boost"}, blocking=True)

    assert vmc.registers[257] == 3
    assert (16, 257, 3) in vmc.writes
    assert hass.states.get(fan).attributes["preset_mode"] == "boost"


@pytest.mark.parametrize(("percentage", "level"), [(0, 0), (25, 0), (50, 1), (75, 2), (100, 3)])
async def test_fan_percentage(hass: HomeAssistant, vmc: FakeVmc, entity_id, percentage: int, level: int) -> None:
    await hass.services.async_call(
        "fan", "set_percentage", {ATTR_ENTITY_ID: entity_id("fan", "ventilation"), "percentage": percentage}, blocking=True
    )
    assert vmc.registers[257] == level


async def test_fan_turn_on_with_preset(hass: HomeAssistant, vmc: FakeVmc, entity_id) -> None:
    await hass.services.async_call(
        "fan", "turn_on", {ATTR_ENTITY_ID: entity_id("fan", "ventilation"), "preset_mode": "cuisine"}, blocking=True
    )
    assert vmc.registers[257] == 2


async def test_level_select(hass: HomeAssistant, vmc: FakeVmc, entity_id) -> None:
    select = entity_id("select", "niveau")
    assert state(hass, select) == "quotidien"
    await hass.services.async_call("select", "select_option", {ATTR_ENTITY_ID: select, "option": "vacances"}, blocking=True)
    assert vmc.registers[257] == 0
    assert state(hass, select) == "vacances"


async def test_bypass_mode_select(hass: HomeAssistant, vmc: FakeVmc, entity_id) -> None:
    select = entity_id("select", "bypass_mode")
    assert state(hass, select) == "automatique"
    await hass.services.async_call(
        "select", "select_option", {ATTR_ENTITY_ID: select, "option": "optimisation_ete"}, blocking=True
    )
    assert vmc.registers[259] == 3


async def test_filter_lifetime(hass: HomeAssistant, vmc: FakeVmc, entity_id) -> None:
    number = entity_id("number", "filtre_duree")
    assert state(hass, number) == "6"
    await hass.services.async_call("number", "set_value", {ATTR_ENTITY_ID: number, "value": 9}, blocking=True)
    assert vmc.registers[267] == 9


async def test_filter_lifetime_is_bounded(hass: HomeAssistant, vmc: FakeVmc, entity_id) -> None:
    with pytest.raises(Exception):
        await hass.services.async_call(
            "number", "set_value", {ATTR_ENTITY_ID: entity_id("number", "filtre_duree"), "value": 24}, blocking=True
        )
    assert vmc.registers[267] == 6


async def test_refused_write_surfaces_an_error(hass: HomeAssistant, vmc: FakeVmc, entity_id) -> None:
    vmc.reject_writes = True
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "select", "select_option", {ATTR_ENTITY_ID: entity_id("select", "niveau"), "option": "boost"}, blocking=True
        )
    assert vmc.registers[257] == 1


async def test_writes_unlock_first(hass: HomeAssistant, vmc: FakeVmc, entity_id) -> None:
    vmc.writes.clear()
    await hass.services.async_call(
        "select", "select_option", {ATTR_ENTITY_ID: entity_id("select", "niveau"), "option": "boost"}, blocking=True
    )
    assert vmc.writes[:2] == [(16, 16, 34102), (16, 257, 3)]
    assert vmc.settings_writes() == [(257, 3)]


async def test_unit_that_stops_answering(
    hass: HomeAssistant, setup_entry: MockConfigEntry, vmc: FakeVmc, entity_id
) -> None:
    vmc.silent = True
    await refresh(hass, setup_entry)
    assert state(hass, entity_id("sensor", "temp_exterieure")) == STATE_UNAVAILABLE
    assert state(hass, entity_id("fan", "ventilation")) == STATE_UNAVAILABLE

    vmc.silent = False
    await refresh(hass, setup_entry)
    assert state(hass, entity_id("sensor", "temp_exterieure")) == "26.04"


async def test_locked_register_is_unknown_not_minus_one(
    hass: HomeAssistant, setup_entry: MockConfigEntry, vmc: FakeVmc, entity_id
) -> None:
    """Un registre qui renvoie -1 (verrouillé ou absent) ne doit jamais s'afficher « -0.01 °C »."""
    vmc.registers[352] = -1
    await refresh(hass, setup_entry)
    assert state(hass, entity_id("sensor", "temp_rejetee")) == STATE_UNKNOWN


async def test_unload(hass: HomeAssistant, setup_entry: MockConfigEntry) -> None:
    assert await hass.config_entries.async_unload(setup_entry.entry_id)
    await hass.async_block_till_done()


async def test_auto_mode_shows_the_applied_level(
    hass: HomeAssistant, setup_entry: MockConfigEntry, vmc: FakeVmc, entity_id
) -> None:
    """En auto, le niveau demandé vaut 255 : seul le registre 1056 dit ce que fait la VMC."""
    vmc.auto_level = 2
    await hass.services.async_call(
        "select", "select_option", {ATTR_ENTITY_ID: entity_id("select", "niveau"), "option": "auto"}, blocking=True
    )
    assert vmc.registers[257] == 255

    fan = hass.states.get(entity_id("fan", "ventilation"))
    assert fan.attributes["preset_mode"] == "auto"
    assert fan.attributes["applied_level"] == "cuisine"
    assert fan.attributes["percentage"] == 75  # celui du niveau appliqué, pas du mode
    assert state(hass, entity_id("sensor", "niveau_en_cours")) == "cuisine"
    assert state(hass, entity_id("select", "niveau")) == "auto"


async def test_applied_level_follows_the_unit_in_auto(
    hass: HomeAssistant, setup_entry: MockConfigEntry, vmc: FakeVmc, entity_id
) -> None:
    """La VMC peut changer de niveau toute seule : l'entité doit suivre."""
    vmc.registers.update({257: 255, 1056: 0, 1057: 10})
    await refresh(hass, setup_entry)
    assert state(hass, entity_id("sensor", "niveau_en_cours")) == "vacances"

    vmc.registers[1056] = 3
    await refresh(hass, setup_entry)
    assert state(hass, entity_id("sensor", "niveau_en_cours")) == "boost"
    assert hass.states.get(entity_id("fan", "ventilation")).attributes["percentage"] == 100


async def test_unit_clock_and_drift(hass: HomeAssistant, setup_entry: MockConfigEntry, vmc: FakeVmc, entity_id) -> None:
    """L'horloge de la VMC dérive : c'est elle qui cadence la programmation horaire."""
    from freezegun import freeze_time

    assert state(hass, entity_id("sensor", "horloge")) == "22/09/2026 21:25:31"

    # La dérive se mesure sur l'heure locale de Home Assistant, pas sur UTC.
    await hass.config.async_set_time_zone("UTC")
    with freeze_time("2026-09-22 22:25:31"):
        await refresh(hass, setup_entry)
        assert state(hass, entity_id("sensor", "derive_horloge")) == "60"


async def test_invalid_clock_is_ignored(hass: HomeAssistant, setup_entry: MockConfigEntry, vmc: FakeVmc, entity_id) -> None:
    vmc.registers.update({1305: 0, 1306: 0})  # horloge non initialisée
    await refresh(hass, setup_entry)
    assert state(hass, entity_id("sensor", "horloge")) == STATE_UNKNOWN
    assert state(hass, entity_id("sensor", "derive_horloge")) == STATE_UNKNOWN


async def test_flow_setpoints_are_read_only_and_optional(
    hass: HomeAssistant, setup_entry: MockConfigEntry, vmc: FakeVmc
) -> None:
    """Les consignes de mise en service sont exposées, mais désactivées par défaut."""
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    entry = registry.async_get_entity_id("sensor", DOMAIN, f"{setup_entry.unique_id}_consigne_extraction_boost")
    assert entry and registry.async_get(entry).disabled_by is er.RegistryEntryDisabler.INTEGRATION

    registry.async_update_entity(entry, disabled_by=None)
    await hass.config_entries.async_reload(setup_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(entry).state == "210"


async def test_a_lost_request_does_not_blank_the_device(
    hass: HomeAssistant, setup_entry: MockConfigEntry, vmc: FakeVmc, entity_id
) -> None:
    """Deux maîtres sur le bus se télescopent : il faut réessayer, pas tout éteindre."""
    vmc.drop_next = 2
    await refresh(hass, setup_entry)
    assert state(hass, entity_id("sensor", "debit_extraction")) == "120"

    vmc.drop_next = 10  # là, la VMC est vraiment injoignable
    await refresh(hass, setup_entry)
    assert state(hass, entity_id("sensor", "debit_extraction")) == STATE_UNAVAILABLE


async def test_boost_returns_to_the_previous_level(
    hass: HomeAssistant, setup_entry: MockConfigEntry, vmc: FakeVmc, entity_id
) -> None:
    """Le Top n'a pas de minuterie de boost : Home Assistant la tient."""
    await hass.services.async_call(
        "number", "set_value", {ATTR_ENTITY_ID: entity_id("number", "boost_duree"), "value": 30}, blocking=True
    )
    await hass.services.async_call(
        "fan", "set_preset_mode", {ATTR_ENTITY_ID: entity_id("fan", "ventilation"), "preset_mode": "boost"}, blocking=True
    )
    assert vmc.registers[257] == 3

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=31))
    await hass.async_block_till_done()
    assert vmc.registers[257] == 1  # retour au niveau d'avant


async def test_boost_timer_is_dropped_when_the_level_changes(
    hass: HomeAssistant, setup_entry: MockConfigEntry, vmc: FakeVmc, entity_id
) -> None:
    select = entity_id("select", "niveau")
    await hass.services.async_call("select", "select_option", {ATTR_ENTITY_ID: select, "option": "boost"}, blocking=True)
    await hass.services.async_call("select", "select_option", {ATTR_ENTITY_ID: select, "option": "cuisine"}, blocking=True)

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=31))
    await hass.async_block_till_done()
    assert vmc.registers[257] == 2  # la minuterie ne doit pas ramener au quotidien


async def test_zero_means_a_permanent_boost(
    hass: HomeAssistant, setup_entry: MockConfigEntry, vmc: FakeVmc, entity_id
) -> None:
    await hass.services.async_call(
        "number", "set_value", {ATTR_ENTITY_ID: entity_id("number", "boost_duree"), "value": 0}, blocking=True
    )
    await hass.services.async_call(
        "select", "select_option", {ATTR_ENTITY_ID: entity_id("select", "niveau"), "option": "boost"}, blocking=True
    )

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(hours=5))
    await hass.async_block_till_done()
    assert vmc.registers[257] == 3


async def test_boost_duration_survives_a_reload(
    hass: HomeAssistant, setup_entry: MockConfigEntry, entity_id
) -> None:
    number = entity_id("number", "boost_duree")
    await hass.services.async_call("number", "set_value", {ATTR_ENTITY_ID: number, "value": 45}, blocking=True)

    await hass.config_entries.async_reload(setup_entry.entry_id)
    await hass.async_block_till_done()
    assert state(hass, number) == "45.0"
