from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import EntityCategory
from homeassistant.helpers import entity_registry as er


async def test_battery_charging_on(hass, setup_integration):
    state = hass.states.get("binary_sensor.vacuum_charging")
    assert state is not None
    # SAMPLE_STATE has charging_state:1 -> charging
    assert state.state == "on"
    assert state.attributes["device_class"] == BinarySensorDeviceClass.BATTERY_CHARGING


async def test_battery_charging_off(hass, setup_integration):
    coordinator = setup_integration.runtime_data.coordinator
    coordinator.async_set_updated_data({**coordinator.data, "charging_state": 2})
    await hass.async_block_till_done()
    state = hass.states.get("binary_sensor.vacuum_charging")
    assert state.state == "off"


async def test_battery_charging_unknown(hass, setup_integration):
    coordinator = setup_integration.runtime_data.coordinator
    data = dict(coordinator.data)
    data.pop("charging_state", None)
    coordinator.async_set_updated_data(data)
    await hass.async_block_till_done()
    state = hass.states.get("binary_sensor.vacuum_charging")
    assert state.state == "unknown"


async def test_mop_pad_attached(hass, setup_integration):
    """SAMPLE_STATE has mop_status:True -> mop pad is attached."""
    state = hass.states.get("binary_sensor.vacuum_mop_pad")
    assert state is not None
    assert state.state == "on"


async def test_mop_pad_detached(hass, setup_integration):
    coordinator = setup_integration.runtime_data.coordinator
    coordinator.async_set_updated_data({**coordinator.data, "mop_status": False})
    await hass.async_block_till_done()
    state = hass.states.get("binary_sensor.vacuum_mop_pad")
    assert state.state == "off"


async def test_mop_pad_unknown(hass, setup_integration):
    coordinator = setup_integration.runtime_data.coordinator
    data = dict(coordinator.data)
    data.pop("mop_status", None)
    coordinator.async_set_updated_data(data)
    await hass.async_block_till_done()
    state = hass.states.get("binary_sensor.vacuum_mop_pad")
    assert state.state == "unknown"


CLEANING_ENTITY_ID = "binary_sensor.vacuum_cleaning_in_progress"


async def _report_status(hass, entry, status: int) -> str:
    coordinator = entry.runtime_data.coordinator
    coordinator.async_set_updated_data({**coordinator.data, "status": status})
    await hass.async_block_till_done()
    return hass.states.get(CLEANING_ENTITY_ID).state


async def test_cleaning_off_while_docked(hass, setup_integration):
    """SAMPLE_STATE has status 2 (charging) -> no job underway."""
    state = hass.states.get(CLEANING_ENTITY_ID)
    assert state is not None
    assert state.state == "off"
    assert state.attributes["device_class"] == BinarySensorDeviceClass.RUNNING
    entry = er.async_get(hass).async_get(CLEANING_ENTITY_ID)
    assert entry.entity_category is EntityCategory.DIAGNOSTIC


async def test_cleaning_stays_on_through_a_mid_job_mop_wash(hass, setup_integration):
    """The X20 Max washes the mop between rooms without ending the job."""
    sweeping, wash_break, station_working, go_wash = 4, 20, 14, 7
    for status in (sweeping, wash_break, station_working, go_wash, sweeping):
        assert await _report_status(hass, setup_integration, status) == "on"


async def test_cleaning_ends_on_the_way_back_to_the_dock(hass, setup_integration):
    """The job ends at go_charging even though the dock keeps working for hours."""
    sweeping, go_charging, go_wash, station_working, charging = 4, 6, 7, 14, 2
    assert await _report_status(hass, setup_integration, sweeping) == "on"
    for status in (go_charging, go_wash, station_working, charging):
        assert await _report_status(hass, setup_integration, status) == "off"


async def test_cleaning_stays_on_while_paused(hass, setup_integration):
    sweeping, paused = 4, 5
    assert await _report_status(hass, setup_integration, sweeping) == "on"
    assert await _report_status(hass, setup_integration, paused) == "on"


async def test_cleaning_ignores_unknown_status(hass, setup_integration):
    sweeping, unpublished_code = 4, 99
    assert await _report_status(hass, setup_integration, sweeping) == "on"
    assert await _report_status(hass, setup_integration, unpublished_code) == "on"
    coordinator = setup_integration.runtime_data.coordinator
    data = dict(coordinator.data)
    data.pop("status", None)
    coordinator.async_set_updated_data(data)
    await hass.async_block_till_done()
    assert hass.states.get(CLEANING_ENTITY_ID).state == "on"


async def _setup_with_restored_state(hass, mock_miot_device, restored: str, status):
    from homeassistant.core import State
    from pytest_homeassistant_custom_component.common import (
        MockConfigEntry,
        mock_restore_cache,
    )

    from custom_components.xiaomi_vacuum.const import (
        CONF_HOST,
        CONF_NAME,
        CONF_TOKEN,
        DOMAIN,
    )
    from tests.conftest import SAMPLE_STATE

    live_state = {**SAMPLE_STATE, "status": status}
    mock_miot_device.get_properties.side_effect = lambda mapping, **_: {
        name: live_state.get(name) for name in mapping
    }
    mock_restore_cache(hass, [State(CLEANING_ENTITY_ID, restored)])
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.50", CONF_TOKEN: "0" * 32, CONF_NAME: "Vacuum"},
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return hass.states.get(CLEANING_ENTITY_ID).state


async def test_cleaning_restores_the_verdict_on_an_inconclusive_status(
    hass, mock_miot_device, enable_custom_integrations
):
    """A restart while the dock washes the mop mid-job keeps the job running."""
    station_working = 14
    state = await _setup_with_restored_state(
        hass, mock_miot_device, "on", station_working
    )
    assert state == "on"


async def test_cleaning_live_status_overrides_the_restored_verdict(
    hass, mock_miot_device, enable_custom_integrations
):
    charging = 2
    state = await _setup_with_restored_state(hass, mock_miot_device, "on", charging)
    assert state == "off"


async def test_cleaning_unknown_without_history_on_an_inconclusive_status(
    hass, mock_miot_device, enable_custom_integrations
):
    station_working = 14
    state = await _setup_with_restored_state(
        hass, mock_miot_device, "unavailable", station_working
    )
    assert state == "unknown"


async def test_cleaning_keeps_the_verdict_through_s40_pro_station_washing(
    hass, setup_integration_ov71
):
    """Station-assisted washing (22-24) happens both mid-job and after it ends."""
    entity_id = "binary_sensor.s40_pro_cleaning_in_progress"
    assert hass.states.get(entity_id).state == "unknown"
    coordinator = setup_integration_ov71.runtime_data.coordinator
    sweeping, go_charge_to_wash, washing, washed, charging = 4, 24, 22, 23, 2
    for status, expected in (
        (sweeping, "on"),
        (go_charge_to_wash, "on"),
        (washing, "on"),
        (washed, "on"),
        (charging, "off"),
        (washing, "off"),
    ):
        coordinator.async_set_updated_data({**coordinator.data, "status": status})
        await hass.async_block_till_done()
        assert hass.states.get(entity_id).state == expected


async def test_cleaning_follows_s20_plus_statuses(hass, setup_integration_b108):
    entity_id = next(
        state.entity_id
        for state in hass.states.async_all("binary_sensor")
        if state.entity_id.endswith("_cleaning_in_progress")
    )
    coordinator = setup_integration_b108.runtime_data.coordinator
    sweeping, break_charging, go_charging = 4, 3, 6
    for status, expected in (
        (sweeping, "on"),
        (break_charging, "on"),
        (go_charging, "off"),
    ):
        coordinator.async_set_updated_data({**coordinator.data, "status": status})
        await hass.async_block_till_done()
        assert hass.states.get(entity_id).state == expected
