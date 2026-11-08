"""End-to-end behaviour for the X20+ (xiaomi.vacuum.c102gl) model.

The X20+ is Dreame-built: its actions sit on different services from every
in-house model (stop is the Dreame stop-clean 4/2, pause is 2/2, locate 7/1),
it publishes no sweep/mop type or clean-times properties, its task status (4.7)
decides the cleaning job instead of the status table, rooms are cleaned through
the Dreame start-clean and listed from the cloud map. Status sequences below are
replayed from a trace of a real sweep-and-mop run.
"""

from __future__ import annotations

import pytest
from homeassistant.components.vacuum.const import VacuumActivity
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ServiceValidationError
from xiaomi_vacuum_sdk import ActionAddress

# Top-level import triggers custom-component loading in the HA pytest harness.
from custom_components.xiaomi_vacuum.const import DOMAIN  # noqa: F401
from custom_components.xiaomi_vacuum.spec import (
    C102GL,
    EntityKey,
    PlainFaultReading,
)

VACUUM_ID = "vacuum.x20_plus"
CLEANING_ID = "binary_sensor.x20_plus_cleaning_in_progress"


async def _report(hass, entry, **values):
    coordinator = entry.runtime_data.coordinator
    coordinator.async_set_updated_data({**coordinator.data, **values})
    await hass.async_block_till_done()


async def test_c102_setup_loads(hass, setup_integration_c102):
    assert setup_integration_c102.state == ConfigEntryState.LOADED


async def test_c102_picks_the_right_spec(hass, setup_integration_c102):
    spec = setup_integration_c102.runtime_data.spec
    assert spec is C102GL
    assert isinstance(spec.fault_reading, PlainFaultReading)
    assert EntityKey.DUST_ARREST_BUTTON in spec.entities
    assert EntityKey.SWEEP_ROUTE_SELECT not in spec.entities
    assert EntityKey.OBSTACLE_AVOIDANCE_SELECT not in spec.entities


MODE_ID = "select.x20_plus_mode"


async def test_c102_creates_the_mode_and_water_level_selects(
    hass, setup_integration_c102
):
    """There is no clean-times property, so no clean-times select."""
    states = {s.entity_id: s for s in hass.states.async_all("select")}
    assert set(states) == {MODE_ID, "select.x20_plus_mop_water_level"}
    water = states["select.x20_plus_mop_water_level"]
    assert water.attributes["options"] == ["level_1", "level_2", "level_3"]
    assert water.state == "level_2"


async def test_c102_mode_reads_the_low_bits_of_the_clean_setting(
    hass, setup_integration_c102
):
    state = hass.states.get(MODE_ID)
    assert state.attributes["options"] == [
        "sweep_mop",
        "mop",
        "sweep",
        "sweep_before_mopping",
    ]
    assert state.state == "sweep_before_mopping"


async def test_c102_mode_write_keeps_the_other_settings(
    hass, setup_integration_c102, mock_miot_device_c102
):
    """Only the two mode bits change; wash frequency and water level stay."""
    from xiaomi_vacuum_sdk import PropertyAddress

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": MODE_ID, "option": "sweep"},
        blocking=True,
    )
    mock_miot_device_c102.set_property.assert_any_call(
        PropertyAddress(siid=4, piid=23), 133122
    )
    assert hass.states.get(MODE_ID).state == "sweep"


async def test_c102_mop_modes_need_the_pads(hass, setup_integration_c102):
    await _report(hass, setup_integration_c102, mop_status=0)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": MODE_ID, "option": "mop"},
            blocking=True,
        )


async def test_c102_creates_the_dock_and_reset_buttons(hass, setup_integration_c102):
    """No stop-mop-wash action on this model, so no button for it."""
    entity_ids = {b.entity_id for b in hass.states.async_all("button")}
    assert entity_ids == {
        "button.x20_plus_collect_dust",
        "button.x20_plus_wash_mop",
        "button.x20_plus_dry_mop",
        "button.x20_plus_stop_drying_mop",
        "button.x20_plus_reset_main_brush",
        "button.x20_plus_reset_side_brush",
        "button.x20_plus_reset_filter",
        "button.x20_plus_reset_mop",
    }


@pytest.mark.parametrize(
    ("button", "address"),
    [
        ("wash_mop", ActionAddress(siid=2, aiid=6)),
        ("dry_mop", ActionAddress(siid=2, aiid=8)),
        ("stop_drying_mop", ActionAddress(siid=2, aiid=9)),
        ("reset_main_brush", ActionAddress(siid=9, aiid=1)),
        ("reset_side_brush", ActionAddress(siid=10, aiid=1)),
        ("reset_filter", ActionAddress(siid=11, aiid=1)),
        ("reset_mop", ActionAddress(siid=18, aiid=1)),
    ],
)
async def test_c102_buttons_fire_their_actions(
    hass, setup_integration_c102, mock_miot_device_c102, button, address
):
    mock_miot_device_c102.call_action.reset_mock()
    await hass.services.async_call(
        "button", "press", {"entity_id": f"button.x20_plus_{button}"}, blocking=True
    )
    mock_miot_device_c102.call_action.assert_called_once_with(address)


@pytest.mark.parametrize(
    ("entity_id", "expected"),
    [
        ("sensor.x20_plus_main_brush_time_left", "120"),
        ("sensor.x20_plus_side_brush_time_left", "80"),
        ("sensor.x20_plus_filter_time_left", "300"),
        ("sensor.x20_plus_mop_time_left", "40"),
        ("sensor.x20_plus_drying_time_left", "0"),
        ("sensor.x20_plus_total_cleanings", "878"),
        ("sensor.x20_plus_total_cleaned_area", "16233"),
    ],
)
async def test_c102_extra_sensors(hass, setup_integration_c102, entity_id, expected):
    assert hass.states.get(entity_id).state == expected


async def test_c102_total_clean_time_shows_in_hours(hass, setup_integration_c102):
    state = hass.states.get("sensor.x20_plus_total_cleaning_time")
    assert state.attributes["unit_of_measurement"] == "h"
    assert float(state.state) == pytest.approx(23000 / 60, abs=0.01)


async def test_c102_unknown_sensor_value(hass, setup_integration_c102):
    await _report(hass, setup_integration_c102, drying_time_left=None)
    state = hass.states.get("sensor.x20_plus_drying_time_left")
    assert state.state == "unknown"


@pytest.mark.parametrize(
    ("entity_id", "state"),
    [
        ("switch.x20_plus_child_lock", "off"),
        ("switch.x20_plus_carpet_boost", "on"),
        ("switch.x20_plus_resume_after_charging", "on"),
        ("switch.x20_plus_do_not_disturb", "on"),
    ],
)
async def test_c102_switches_follow_the_device(
    hass, setup_integration_c102, entity_id, state
):
    assert hass.states.get(entity_id).state == state


@pytest.mark.parametrize(
    ("entity_id", "service", "write"),
    [
        ("switch.x20_plus_child_lock", "turn_on", ((4, 27), 1)),
        ("switch.x20_plus_carpet_boost", "turn_off", ((4, 12), 0)),
        ("switch.x20_plus_resume_after_charging", "turn_off", ((4, 11), 0)),
        # The do-not-disturb flag is a real bool on the device.
        ("switch.x20_plus_do_not_disturb", "turn_off", ((5, 1), False)),
    ],
)
@pytest.mark.usefixtures("setup_integration_c102")
async def test_c102_switches_write_the_device_type(
    hass, mock_miot_device_c102, entity_id, service, write
):
    from xiaomi_vacuum_sdk import PropertyAddress

    mock_miot_device_c102.set_property.reset_mock()
    await hass.services.async_call(
        "switch", service, {"entity_id": entity_id}, blocking=True
    )
    (siid, piid), value = write
    (sent_address, sent_value), _ = mock_miot_device_c102.set_property.call_args
    assert sent_address == PropertyAddress(siid=siid, piid=piid)
    assert sent_value == value
    assert type(sent_value) is type(value)
    assert hass.states.get(entity_id).state == ("on" if service == "turn_on" else "off")


async def test_c102_switch_unknown_state(hass, setup_integration_c102):
    await _report(hass, setup_integration_c102, child_lock=None)
    assert hass.states.get("switch.x20_plus_child_lock").state == "unknown"


async def test_c102_volume(hass, setup_integration_c102, mock_miot_device_c102):
    from xiaomi_vacuum_sdk import PropertyAddress

    state = hass.states.get("number.x20_plus_volume")
    assert float(state.state) == 75
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.x20_plus_volume", "value": 40},
        blocking=True,
    )
    mock_miot_device_c102.set_property.assert_any_call(
        PropertyAddress(siid=7, piid=1), 40
    )
    assert float(hass.states.get("number.x20_plus_volume").state) == 40
    await _report(hass, setup_integration_c102, volume=None)
    assert hass.states.get("number.x20_plus_volume").state == "unknown"


async def test_c102_without_cloud_has_no_map_image(hass, setup_integration_c102):
    """The map needs the cloud session; without it the entity never gets data."""
    assert setup_integration_c102.runtime_data.map_coordinator is None


async def test_c102_renders_the_dreame_map(
    hass, setup_integration_c102_with_cloud, mock_cloud
):
    """The Dreame blob goes through the SDK's Dreame decoder, not the Xiaomi one."""
    entry = setup_integration_c102_with_cloud
    assert entry.state == ConfigEntryState.LOADED
    mock_cloud.async_get_map_bytes.assert_any_await("1234/567/map.bin")
    rendered = entry.runtime_data.map_coordinator.data
    assert rendered["png"].startswith(b"\x89PNG")
    assert rendered["calibration"]["resolution"] == 50
    assert hass.states.get("image.x20_plus_map") is not None


async def test_c102_undecodable_map_keeps_the_last_image(
    hass, setup_integration_c102_with_cloud, mock_cloud
):
    coordinator = setup_integration_c102_with_cloud.runtime_data.map_coordinator
    before = coordinator.data
    mock_cloud.async_get_map_bytes.return_value = b"AAAA,encrypted"
    await coordinator.async_refresh()
    assert coordinator.data == before


async def test_c102_mop_pad_follows_the_waterbox_status(hass, setup_integration_c102):
    assert hass.states.get("binary_sensor.x20_plus_mop_pad").state == "on"
    await _report(hass, setup_integration_c102, mop_status=0)
    assert hass.states.get("binary_sensor.x20_plus_mop_pad").state == "off"


async def test_c102_docked_with_the_mop_notice_is_not_an_error(
    hass, setup_integration_c102
):
    """Fault 68 shows while docked with the pads on; the vacuum stays docked."""
    state = hass.states.get(VACUUM_ID)
    assert state.state == VacuumActivity.DOCKED
    assert state.attributes["fan_speed"] == "basic"
    assert hass.states.get("sensor.x20_plus_error_code").state == "68"
    assert hass.states.get("sensor.x20_plus_status").state == "charged"


async def test_c102_wash_tray_reminder_is_not_an_error(hass, setup_integration_c102):
    """Fault 114 asks to rinse the mop-wash tray after a mop job, while drying."""
    await _report(hass, setup_integration_c102, fault=114, status=8, task_status=0)
    assert hass.states.get(VACUUM_ID).state == VacuumActivity.DOCKED
    assert hass.states.get("sensor.x20_plus_error_code").state == "114"


async def test_c102_real_fault_forces_error(hass, setup_integration_c102):
    await _report(hass, setup_integration_c102, fault=1, status=1, task_status=1)
    assert hass.states.get(VACUUM_ID).state == VacuumActivity.ERROR


@pytest.mark.parametrize(
    ("service", "address"),
    [
        ("start", ActionAddress(siid=2, aiid=1)),
        ("pause", ActionAddress(siid=2, aiid=2)),
        ("stop", ActionAddress(siid=4, aiid=2)),
        ("return_to_base", ActionAddress(siid=3, aiid=1)),
        ("locate", ActionAddress(siid=7, aiid=1)),
    ],
)
async def test_c102_vacuum_services_hit_the_dreame_actions(
    hass, setup_integration_c102, mock_miot_device_c102, service, address
):
    mock_miot_device_c102.call_action.reset_mock()
    await hass.services.async_call(
        "vacuum", service, {"entity_id": VACUUM_ID}, blocking=True
    )
    mock_miot_device_c102.call_action.assert_any_call(address)


async def test_c102_fan_speed_writes_the_zero_based_value(
    hass, setup_integration_c102, mock_miot_device_c102
):
    from xiaomi_vacuum_sdk import PropertyAddress

    await hass.services.async_call(
        "vacuum",
        "set_fan_speed",
        {"entity_id": VACUUM_ID, "fan_speed": "full_speed"},
        blocking=True,
    )
    mock_miot_device_c102.set_property.assert_any_call(
        PropertyAddress(siid=2, piid=3), 3
    )


def _vacuum(hass):
    return hass.data["entity_components"]["vacuum"].get_entity(VACUUM_ID)


async def test_c102_room_clean_sends_the_dreame_segment_clean(
    hass, setup_integration_c102, mock_miot_device_c102
):
    """Rooms go in the given order, with the current fan speed and water level."""
    mock_miot_device_c102.call_action.reset_mock()
    await _vacuum(hass).async_clean_segments(["4", "1"])
    mock_miot_device_c102.call_action.assert_called_once_with(
        ActionAddress(siid=4, aiid=1),
        [
            {"piid": 1, "value": 18},
            {"piid": 10, "value": '{"selects":[[4,1,1,2,1],[1,1,1,2,2]]}'},
        ],
    )
    assert hass.states.get(VACUUM_ID).state == VacuumActivity.CLEANING


async def test_c102_room_clean_needs_the_fan_speed_and_water_level(
    hass, setup_integration_c102, mock_miot_device_c102
):
    """An unanswered settings read must not send a selection with nulls."""
    from custom_components.xiaomi_vacuum.api import XiaomiVacuumApiClientError

    mock_miot_device_c102.call_action.reset_mock()
    mock_miot_device_c102.get_properties.side_effect = lambda mapping, **_: (
        dict.fromkeys(mapping)
    )
    with pytest.raises(XiaomiVacuumApiClientError):
        await _vacuum(hass).async_clean_segments(["1"])
    mock_miot_device_c102.call_action.assert_not_called()


async def test_c102_advertises_area_cleaning(hass, setup_integration_c102):
    from homeassistant.components.vacuum.const import VacuumEntityFeature

    assert _vacuum(hass).supported_features & VacuumEntityFeature.CLEAN_AREA


async def test_area_cleaning_hidden_without_room_clean_actions(
    hass, setup_integration_c102
):
    """A model missing its strategy's actions never offers clean_area."""
    from dataclasses import replace

    from homeassistant.components.vacuum.const import VacuumEntityFeature

    spec = setup_integration_c102.runtime_data.spec
    setup_integration_c102.runtime_data.spec = replace(spec, room_cleaning=None)
    features = _vacuum(hass).supported_features
    assert not features & VacuumEntityFeature.CLEAN_AREA
    assert features & VacuumEntityFeature.START


async def test_c102_room_clean_rejects_a_non_numeric_room(
    hass, setup_integration_c102, mock_miot_device_c102
):
    from custom_components.xiaomi_vacuum.api import XiaomiVacuumApiClientError

    mock_miot_device_c102.call_action.reset_mock()
    with pytest.raises(XiaomiVacuumApiClientError):
        await _vacuum(hass).async_clean_segments(["kitchen"])
    mock_miot_device_c102.call_action.assert_not_called()


async def test_c102_rooms_come_from_the_map_coordinator(
    hass, setup_integration_c102_with_cloud, mock_cloud, dreame_map, dreame_name
):
    """No second download: the rooms ride along with the rendered map."""
    coordinator = setup_integration_c102_with_cloud.runtime_data.map_coordinator
    mock_cloud.async_get_map_bytes.return_value = dreame_map(
        {
            "5": {"name": dreame_name("Escritório"), "type": 0},
            "1": {"name": dreame_name("Living room"), "type": 0},
            # Never named: the app lists it as "Room 4", so HA does too.
            "4": {"nei_id": [1]},
        }
    )
    await coordinator.async_refresh()
    mock_cloud.async_get_map_bytes.reset_mock()
    segments = await _vacuum(hass).async_get_segments()
    mock_cloud.async_get_map_bytes.assert_not_awaited()
    assert [(s.id, s.name) for s in segments] == [
        ("1", "Living room"),
        ("4", "Room 4"),
        ("5", "Escritório"),
    ]


async def test_c102_rooms_survive_an_undecodable_map(
    hass, setup_integration_c102_with_cloud, mock_cloud
):
    coordinator = setup_integration_c102_with_cloud.runtime_data.map_coordinator
    first = await _vacuum(hass).async_get_segments()
    assert [s.name for s in first] == ["Living room"]
    mock_cloud.async_get_map_bytes.return_value = b"garbage"
    await coordinator.async_refresh()
    assert await _vacuum(hass).async_get_segments() == first


async def test_c102_rooms_need_the_cloud(hass, setup_integration_c102):
    assert await _vacuum(hass).async_get_segments() == []


async def test_c102_rooms_are_restored_with_the_cached_map(
    hass, setup_integration_c102_with_cloud
):
    """The rooms are saved with the PNG, so they survive a restart."""
    coordinator = setup_integration_c102_with_cloud.runtime_data.map_coordinator
    stored = await coordinator._store.async_load()
    assert stored["rooms"] == [{"id": "1", "name": "Living room"}]
    coordinator.async_set_updated_data(None)
    await coordinator.async_load_cached()
    assert coordinator.data["rooms"] == [{"id": "1", "name": "Living room"}]


async def test_c102_cleaning_follows_the_task_status_through_a_mop_run(
    hass, setup_integration_c102
):
    """Traced run: pre-wash, mid-job wash and recharge, back home, final wash."""
    entry = setup_integration_c102
    assert hass.states.get(CLEANING_ID).state == "off"
    job = [
        (12, 1),  # sweeping and mopping
        (9, 1),  # pre-wash in the dock before leaving
        (12, 1),
        (10, 1),  # driving back to wash mid-job
        (6, 1),  # charging contact for ~2 s
        (9, 1),  # mid-job wash
        (12, 1),
        (5, 1),  # driving home at the end, task still open
    ]
    for status, task_status in job:
        await _report(hass, entry, status=status, task_status=task_status, fault=0)
        assert hass.states.get(CLEANING_ID).state == "on", status
    after = [(6, 0), (22, 0), (9, 0), (8, 0)]  # docked, dust, final wash, drying
    for status, task_status in after:
        await _report(hass, entry, status=status, task_status=task_status)
        assert hass.states.get(CLEANING_ID).state == "off", status


async def test_c102_manual_dock_ends_the_job(hass, setup_integration_c102):
    """Tapping Dock mid-job drops the task status to 0 straight away."""
    entry = setup_integration_c102
    await _report(hass, entry, status=3, task_status=6, fault=0)
    assert hass.states.get(CLEANING_ID).state == "on"
    await _report(hass, entry, status=5, task_status=0)
    assert hass.states.get(CLEANING_ID).state == "off"


def test_c102_spec_registers_the_dock_actions_as_commands():
    assert set(C102GL.send_commands) == {
        "continue_sweep",
        "start_mop_wash",
        "start_dry",
        "stop_dry",
    }
    assert C102GL.actions.start_only_sweep is None
    assert C102GL.actions.start_mop is None
    assert C102GL.actions.start_sweep_mop is None


def test_c102_entities_skip_the_unmapped_properties():
    entities = C102GL.entities
    assert EntityKey.MAP_IMAGE in entities
    assert EntityKey.MOP_PAD_SENSOR in entities
    assert EntityKey.MOP_WATER_LEVEL_SELECT in entities
    assert EntityKey.DUST_ARREST_BUTTON in entities
    assert EntityKey.SWEEP_MOP_TYPE_SELECT in entities
    for key in (
        EntityKey.CLEAN_TIMES_SELECT,
        EntityKey.STOP_MOP_WASH_BUTTON,
        EntityKey.SWEEP_ROUTE_SELECT,
        EntityKey.OBSTACLE_AVOIDANCE_SELECT,
    ):
        assert key not in entities


def test_c102_status_follows_the_selected_mode():
    assert C102GL.status_slugs[1] == "sweeping"
    assert C102GL.status_slugs[7] == "mopping"
    assert C102GL.status_slugs[12] == "sweeping_and_mopping"
    for code in (1, 7, 12):
        assert C102GL.status_to_activity[code] is VacuumActivity.CLEANING


def test_c102_charging_state_knows_go_charging():
    assert C102GL.charging_state_slugs[5] == "go_charging"


async def test_c102_without_a_fan_speed_table_does_not_offer_fan_speeds(
    hass, setup_integration_c102
):
    from dataclasses import replace

    from homeassistant.components.vacuum.const import VacuumEntityFeature

    spec = setup_integration_c102.runtime_data.spec
    setup_integration_c102.runtime_data.spec = replace(spec, fan_speeds={})
    features = _vacuum(hass).supported_features
    assert not features & VacuumEntityFeature.FAN_SPEED
    assert features & VacuumEntityFeature.START
