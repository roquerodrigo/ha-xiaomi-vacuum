from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState


async def test_setup_entry_loads(hass, setup_integration):
    assert setup_integration.state == ConfigEntryState.LOADED


async def test_setup_entry_creates_runtime_data(hass, setup_integration):
    rt = setup_integration.runtime_data
    assert rt.client is not None
    assert rt.coordinator is not None
    assert rt.info is not None


async def test_setup_entry_creates_vacuum_entity(hass, setup_integration):
    states = hass.states.async_all("vacuum")
    assert len(states) == 1


async def test_setup_entry_creates_select_entities(hass, setup_integration):
    states = hass.states.async_all("select")
    assert len(states) == 5


async def test_unload_entry(hass, setup_integration):
    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()
    assert setup_integration.state == ConfigEntryState.NOT_LOADED


async def test_reload_entry(hass, setup_integration):
    await hass.config_entries.async_reload(setup_integration.entry_id)
    await hass.async_block_till_done()
    assert setup_integration.state == ConfigEntryState.LOADED
