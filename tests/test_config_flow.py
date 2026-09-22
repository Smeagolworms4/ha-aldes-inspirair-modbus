"""Ajout, options et reconfiguration, exécutés dans Home Assistant."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aldes_inspirair.const import CONF_SCAN_INTERVAL, CONF_SLAVE, DOMAIN

from .fake_vmc import FakeVmc


async def test_user_flow_creates_entry(hass: HomeAssistant, vmc: FakeVmc, entry_data: dict) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], entry_data)
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "VMC Aldes"
    assert result["data"] == entry_data
    assert result["result"].unique_id == "127.0.0.1:2"


async def test_silent_unit_is_reported(hass: HomeAssistant, vmc: FakeVmc, entry_data: dict) -> None:
    vmc.silent = True
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], entry_data)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_same_unit_twice_is_refused(hass: HomeAssistant, setup_entry: MockConfigEntry, entry_data: dict) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], entry_data)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_change_polling_interval(hass: HomeAssistant, setup_entry: MockConfigEntry) -> None:
    result = await hass.config_entries.options.async_init(setup_entry.entry_id)
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_SCAN_INTERVAL: 60})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert setup_entry.options == {CONF_SCAN_INTERVAL: 60}
    assert setup_entry.runtime_data.update_interval.total_seconds() == 60


async def test_reconfigure_keeps_the_entities(
    hass: HomeAssistant, setup_entry: MockConfigEntry, vmc: FakeVmc
) -> None:
    """Changer l'adresse de la passerelle ne doit pas changer l'identifiant unique."""
    other = FakeVmc()
    await other.start()
    try:
        result = await setup_entry.start_reconfigure_flow(hass)
        assert result["step_id"] == "reconfigure"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: "127.0.0.1", CONF_PORT: other.port, CONF_SLAVE: 2}
        )
        await hass.async_block_till_done()

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "reconfigure_successful"
        assert setup_entry.data[CONF_PORT] == other.port
        assert setup_entry.unique_id == "127.0.0.1:2"
    finally:
        await hass.config_entries.async_unload(setup_entry.entry_id)
        await other.stop()
