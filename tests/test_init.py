from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState

from custom_components.xiaomi_vacuum import async_reload_entry
from custom_components.xiaomi_vacuum.api import (
    XiaomiVacuumApiClientCommunicationError,
)
from custom_components.xiaomi_vacuum.const import (
    CONF_CLOUD_COUNTRY,
    CONF_CLOUD_SERVICE_TOKEN,
    CONF_CLOUD_SSECURITY,
    CONF_CLOUD_USER_ID,
    CONF_HOST,
    CONF_NAME,
    CONF_TOKEN,
    DOMAIN,
)


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


async def test_async_reload_entry_listener(hass, setup_integration):
    with patch.object(
        hass.config_entries, "async_reload", AsyncMock(return_value=True)
    ) as reload:
        await async_reload_entry(hass, setup_integration)
    reload.assert_awaited_once_with(setup_integration.entry_id)


async def test_setup_entry_not_ready_on_communication_error(
    hass, mock_miot_device, enable_custom_integrations
):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.1.50",
            CONF_TOKEN: "0" * 32,
            CONF_NAME: "Aspirador",
        },
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.xiaomi_vacuum.XiaomiVacuumApiClient.async_get_info",
        AsyncMock(side_effect=XiaomiVacuumApiClientCommunicationError("offline")),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.SETUP_RETRY


async def test_setup_entry_warns_when_cloud_session_invalid(
    hass, mock_miot_device, enable_custom_integrations
):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.xiaomi_vacuum.cloud import XiaomiCloudError

    cloud = AsyncMock()
    cloud.async_resolve_device = AsyncMock(
        side_effect=XiaomiCloudError("session expired")
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.1.50",
            CONF_TOKEN: "0" * 32,
            CONF_NAME: "Aspirador",
            CONF_CLOUD_COUNTRY: "cn",
            CONF_CLOUD_SSECURITY: "ssec",
            CONF_CLOUD_SERVICE_TOKEN: "tok",
            CONF_CLOUD_USER_ID: "uid",
        },
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.xiaomi_vacuum.XiaomiCloud.from_session",
        return_value=cloud,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # Setup still succeeds; only the map coordinator is skipped.
    assert entry.state == ConfigEntryState.LOADED
    assert entry.runtime_data.map_coordinator is None
