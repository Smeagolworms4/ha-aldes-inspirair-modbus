"""Fixtures : une fausse VMC sur 127.0.0.1 et l'intégration chargée dans Home Assistant."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.aldes_inspirair.const import CONF_SLAVE, DOMAIN

from .fake_vmc import FakeVmc

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Rend `custom_components/aldes_inspirair` visible par Home Assistant."""
    yield


@pytest.fixture
async def vmc(socket_enabled) -> FakeVmc:
    fake = FakeVmc()
    await fake.start()
    yield fake
    await fake.stop()


@pytest.fixture
def entry_data(vmc: FakeVmc) -> dict:
    return {CONF_HOST: "127.0.0.1", CONF_PORT: vmc.port, CONF_SLAVE: 2}


@pytest.fixture
async def setup_entry(hass: HomeAssistant, entry_data: dict) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="VMC Aldes", data=entry_data, unique_id="127.0.0.1:2")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.fixture
def entity_id(hass: HomeAssistant, setup_entry: MockConfigEntry):
    """Retrouve une entité par sa clé, indépendamment de la langue."""

    def _lookup(platform: str, key: str) -> str:
        found = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{setup_entry.unique_id}_{key}")
        assert found, f"{platform}.{key} absente"
        return found

    return _lookup
