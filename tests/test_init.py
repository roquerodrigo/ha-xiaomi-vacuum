from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState

from custom_components.xiaomi_vacuum.api import (
    XiaomiVacuumApiClientCommunicationError,
)
from custom_components.xiaomi_vacuum.const import (
    CONF_CLOUD_COUNTRY,
    CONF_CLOUD_DEVICE,
    CONF_CLOUD_SERVICE_TOKEN,
    CONF_CLOUD_SSECURITY,
    CONF_CLOUD_USER_ID,
    CONF_DEVICE_INFO,
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
    assert len(states) == 12


async def test_unload_entry(hass, setup_integration):
    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()
    assert setup_integration.state == ConfigEntryState.NOT_LOADED


async def test_reload_entry(hass, setup_integration):
    await hass.config_entries.async_reload(setup_integration.entry_id)
    await hass.async_block_till_done()
    assert setup_integration.state == ConfigEntryState.LOADED


async def test_setup_entry_not_ready_on_communication_error(
    hass, mock_miot_device, enable_custom_integrations
):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.1.50",
            CONF_TOKEN: "0" * 32,
            CONF_NAME: "Vacuum",
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


async def test_setup_persists_device_info_on_success(hass, setup_integration):
    assert setup_integration.data[CONF_DEVICE_INFO] == {
        "model": "xiaomi.vacuum.d109gl",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "firmware_version": "1.0.0",
        "hardware_version": "rev1",
    }


async def test_setup_offline_with_cached_info_loads(
    hass, mock_miot_device, enable_custom_integrations
):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.1.50",
            CONF_TOKEN: "0" * 32,
            CONF_NAME: "Vacuum",
            CONF_DEVICE_INFO: {
                "model": "xiaomi.vacuum.d109gl",
                "mac_address": "AA:BB:CC:DD:EE:FF",
                "firmware_version": "1.0.0",
                "hardware_version": "rev1",
            },
        },
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)
    offline = XiaomiVacuumApiClientCommunicationError("offline")
    with (
        patch(
            "custom_components.xiaomi_vacuum.XiaomiVacuumApiClient.async_get_info",
            AsyncMock(side_effect=offline),
        ),
        patch(
            "custom_components.xiaomi_vacuum.XiaomiVacuumApiClient.async_get_state",
            AsyncMock(side_effect=offline),
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.LOADED
    vacuum = hass.states.async_all("vacuum")
    assert len(vacuum) == 1
    assert vacuum[0].state == "unavailable"

    from homeassistant.helpers import issue_registry as ir

    registry = ir.async_get(hass)
    issue = registry.async_get_issue(DOMAIN, f"cannot_connect_{entry.entry_id}")
    assert issue is not None
    assert issue.translation_placeholders == {
        "name": entry.title,
        "host": "192.168.1.50",
    }


async def test_remove_entry_clears_repair_issues(
    hass, mock_miot_device, enable_custom_integrations
):
    from homeassistant.helpers import issue_registry as ir
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.1.50",
            CONF_TOKEN: "0" * 32,
            CONF_NAME: "Vacuum",
            CONF_DEVICE_INFO: {
                "model": "xiaomi.vacuum.d109gl",
                "mac_address": "AA:BB:CC:DD:EE:FF",
                "firmware_version": "1.0.0",
                "hardware_version": "rev1",
            },
        },
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)
    offline = XiaomiVacuumApiClientCommunicationError("offline")
    with (
        patch(
            "custom_components.xiaomi_vacuum.XiaomiVacuumApiClient.async_get_info",
            AsyncMock(side_effect=offline),
        ),
        patch(
            "custom_components.xiaomi_vacuum.XiaomiVacuumApiClient.async_get_state",
            AsyncMock(side_effect=offline),
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    registry = ir.async_get(hass)
    issue_id = f"cannot_connect_{entry.entry_id}"
    assert registry.async_get_issue(DOMAIN, issue_id) is not None

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get_issue(DOMAIN, issue_id) is None


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
            CONF_NAME: "Vacuum",
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


async def test_setup_entry_starts_reauth_when_cloud_session_invalid(
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
            CONF_NAME: "Vacuum",
            CONF_CLOUD_COUNTRY: "cn",
            CONF_CLOUD_SSECURITY: "ssec",
            CONF_CLOUD_SERVICE_TOKEN: "tok",
            CONF_CLOUD_USER_ID: "uid",
        },
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.xiaomi_vacuum.XiaomiCloud.from_session",
            return_value=cloud,
        ),
        patch.object(MockConfigEntry, "async_start_reauth") as start_reauth,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # The invalid cloud session surfaces a reauth prompt, but the entry stays
    # loaded so the local (miIO) entities keep working.
    start_reauth.assert_called_once()
    assert entry.state == ConfigEntryState.LOADED
    assert len(hass.states.async_all("vacuum")) == 1


async def test_setup_entry_loads_and_starts_reauth_when_service_token_expired(
    hass, mock_miot_device, enable_custom_integrations
):
    """An expired serviceToken must prompt reauth, never hold the entry in retry."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.xiaomi_vacuum.cloud import XiaomiCloudAuthError

    cloud = AsyncMock()
    cloud.async_resolve_device = AsyncMock(
        side_effect=XiaomiCloudAuthError(
            "Xiaomi cloud rejected the session (HTTP 426: SERVICETOKEN_EXPIRED)"
        )
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.1.50",
            CONF_TOKEN: "0" * 32,
            CONF_NAME: "Vacuum",
            CONF_CLOUD_COUNTRY: "us",
            CONF_CLOUD_SSECURITY: "ssec",
            CONF_CLOUD_SERVICE_TOKEN: "tok",
            CONF_CLOUD_USER_ID: "uid",
        },
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.xiaomi_vacuum.XiaomiCloud.from_session",
            return_value=cloud,
        ),
        patch.object(MockConfigEntry, "async_start_reauth") as start_reauth,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.LOADED
    assert entry.runtime_data.map_coordinator is None
    assert len(hass.states.async_all("vacuum")) == 1
    start_reauth.assert_called_once()


async def test_setup_entry_retries_when_cloud_unreachable(
    hass, mock_miot_device, enable_custom_integrations
):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.xiaomi_vacuum.cloud import XiaomiCloudConnectionError

    cloud = AsyncMock()
    cloud.async_resolve_device = AsyncMock(
        side_effect=XiaomiCloudConnectionError("dns not ready")
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.1.50",
            CONF_TOKEN: "0" * 32,
            CONF_NAME: "Vacuum",
            CONF_CLOUD_COUNTRY: "us",
            CONF_CLOUD_SSECURITY: "ssec",
            CONF_CLOUD_SERVICE_TOKEN: "tok",
            CONF_CLOUD_USER_ID: "uid",
        },
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.xiaomi_vacuum.XiaomiCloud.from_session",
            return_value=cloud,
        ),
        patch.object(MockConfigEntry, "async_start_reauth") as start_reauth,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # A cloud network failure is transient (e.g. DNS not up during host boot):
    # the entry must retry, and must not be mistaken for an expired session.
    assert entry.state == ConfigEntryState.SETUP_RETRY
    start_reauth.assert_not_called()


async def test_setup_unknown_model_raises_unsupported_repair(
    hass, mock_miot_device, enable_custom_integrations
):
    """An unknown model must fall back to the default spec and raise a repair."""
    from homeassistant.helpers import issue_registry as ir
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    mock_miot_device.info.return_value.model = "xiaomi.vacuum.unknown"

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.1.50",
            CONF_TOKEN: "0" * 32,
            CONF_NAME: "Mystery Vac",
        },
        unique_id="AA:BB:CC:DD:EE:00",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.LOADED
    issue = ir.async_get(hass).async_get_issue(
        DOMAIN, f"unsupported_model_{entry.entry_id}"
    )
    assert issue is not None
    assert issue.translation_placeholders["model"] == "xiaomi.vacuum.unknown"


CACHED_CLOUD_DEVICE = {
    "device_id": "d",
    "name": "Vacuum",
    "model": "xiaomi.vacuum.d109gl",
    "country": "cn",
    "local_ip": None,
    "mac": None,
}


def _cloud_entry(cloud_device=None):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    data = {
        CONF_HOST: "192.168.1.50",
        CONF_TOKEN: "0" * 32,
        CONF_NAME: "Vacuum",
        CONF_CLOUD_COUNTRY: "cn",
        CONF_CLOUD_SSECURITY: "ssec",
        CONF_CLOUD_SERVICE_TOKEN: "tok",
        CONF_CLOUD_USER_ID: "uid",
    }
    if cloud_device is not None:
        data[CONF_CLOUD_DEVICE] = cloud_device
    return MockConfigEntry(domain=DOMAIN, data=data, unique_id="AA:BB:CC:DD:EE:FF")


async def test_setup_persists_the_resolved_cloud_device(
    hass, setup_integration_with_cloud, mock_cloud
):
    mock_cloud.async_resolve_device.assert_awaited_once_with("0" * 32)
    assert setup_integration_with_cloud.data[CONF_CLOUD_DEVICE] == CACHED_CLOUD_DEVICE


async def test_setup_reuses_the_cached_cloud_device_without_waiting(
    hass, mock_miot_device, mock_cloud, enable_custom_integrations
):
    from custom_components.xiaomi_vacuum.cloud import XiaomiDeviceInfo

    lookup_done = asyncio.Event()

    async def slow_lookup(token):
        await lookup_done.wait()
        return mock_cloud.async_resolve_device.return_value

    mock_cloud.async_resolve_device.side_effect = slow_lookup
    entry = _cloud_entry(CACHED_CLOUD_DEVICE)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Loaded while the cloud lookup is still pending.
    assert entry.state == ConfigEntryState.LOADED
    assert entry.runtime_data.map_coordinator is not None
    mock_cloud.restore_device.assert_called_once_with(
        XiaomiDeviceInfo("d", "Vacuum", "xiaomi.vacuum.d109gl", "0" * 32, "cn")
    )

    lookup_done.set()
    await hass.async_block_till_done(wait_background_tasks=True)
    mock_cloud.async_resolve_device.assert_awaited_once_with("0" * 32)
    assert entry.data[CONF_CLOUD_DEVICE] == CACHED_CLOUD_DEVICE


async def test_cached_cloud_device_from_another_region_is_resolved_again(
    hass, mock_miot_device, mock_cloud, enable_custom_integrations
):
    entry = _cloud_entry({**CACHED_CLOUD_DEVICE, "country": "de"})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)

    mock_cloud.restore_device.assert_not_called()
    mock_cloud.async_resolve_device.assert_awaited_once()
    assert entry.data[CONF_CLOUD_DEVICE] == CACHED_CLOUD_DEVICE


async def test_background_check_updates_a_changed_cloud_device(
    hass, mock_miot_device, mock_cloud, enable_custom_integrations
):
    entry = _cloud_entry({**CACHED_CLOUD_DEVICE, "name": "Old name"})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)

    assert entry.data[CONF_CLOUD_DEVICE] == CACHED_CLOUD_DEVICE


async def test_background_check_tolerates_an_unreachable_cloud(
    hass, mock_miot_device, mock_cloud, enable_custom_integrations
):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.xiaomi_vacuum.cloud import XiaomiCloudConnectionError

    mock_cloud.async_resolve_device.side_effect = XiaomiCloudConnectionError("dns")
    entry = _cloud_entry(CACHED_CLOUD_DEVICE)
    entry.add_to_hass(hass)
    with patch.object(MockConfigEntry, "async_start_reauth") as start_reauth:
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)

    # The cached device keeps the entry loaded instead of retrying setup.
    assert entry.state == ConfigEntryState.LOADED
    assert entry.runtime_data.map_coordinator is not None
    start_reauth.assert_not_called()


async def test_background_check_starts_reauth_when_session_rejected(
    hass, mock_miot_device, mock_cloud, enable_custom_integrations
):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.xiaomi_vacuum.cloud import XiaomiCloudAuthError

    mock_cloud.async_resolve_device.side_effect = XiaomiCloudAuthError("expired")
    entry = _cloud_entry(CACHED_CLOUD_DEVICE)
    entry.add_to_hass(hass)
    with patch.object(MockConfigEntry, "async_start_reauth") as start_reauth:
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)

    assert entry.state == ConfigEntryState.LOADED
    start_reauth.assert_called_once()


async def test_map_download_does_not_block_setup(
    hass, mock_miot_device_c102, mock_cloud, enable_custom_integrations
):
    from tests.conftest import b64_name, build_dreame_map

    download_done = asyncio.Event()
    map_blob = build_dreame_map({"1": {"name": b64_name("Living room")}})

    async def slow_download(obj_name):
        await download_done.wait()
        return map_blob

    mock_cloud.async_fault_text = AsyncMock(return_value=None)
    mock_cloud.async_get_map_bytes = AsyncMock(side_effect=slow_download)
    entry = _cloud_entry(CACHED_CLOUD_DEVICE)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Entities exist before the map lands; the image waits for its first PNG.
    assert entry.state == ConfigEntryState.LOADED
    map_coordinator = entry.runtime_data.map_coordinator
    assert map_coordinator.data is None
    image = next(iter(hass.states.async_entity_ids("image")))
    assert hass.states.get(image).state == "unavailable"

    download_done.set()
    await hass.async_block_till_done(wait_background_tasks=True)
    assert map_coordinator.data["png"].startswith(b"\x89PNG")
    assert hass.states.get(image).state != "unavailable"
