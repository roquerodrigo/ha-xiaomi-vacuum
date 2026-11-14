"""End-to-end behaviour for the X20 Max (xiaomi.vacuum.d109gl) model.

Mirror of ``test_b108.py``: the X20 Max must get the sweep-route /
obstacle-avoidance selects, the dust-arrest button (it has that hardware) and
the consumable hours-left sensors and life reset buttons; its return-home must
hit the vacuum service (SIID 2 / aiid 3, not the battery service like the S20+),
and the live ``Fault Ids`` JSON list must be parsed.
"""

from __future__ import annotations

import json

import pytest
from homeassistant.config_entries import ConfigEntryState
from xiaomi_vacuum_sdk import ActionAddress

# Top-level import triggers custom-component loading in the HA pytest harness;
# without it `from custom_components.xiaomi_vacuum...` inside tests fails with
# AttributeError until another test file imports the package first.
from custom_components.xiaomi_vacuum.const import DOMAIN
from custom_components.xiaomi_vacuum.spec import (
    D109GL,
    EntityKey,
    FaultIdsReading,
    Property,
)


async def test_d109_setup_loads(hass, setup_integration):
    assert setup_integration.state == ConfigEntryState.LOADED


async def test_d109_picks_the_right_spec(hass, setup_integration):

    spec = setup_integration.runtime_data.spec
    assert spec.model == "xiaomi.vacuum.d109gl"
    assert isinstance(spec.fault_reading, FaultIdsReading)
    assert EntityKey.DUST_ARREST_BUTTON in spec.entities
    assert EntityKey.SWEEP_ROUTE_SELECT in spec.entities
    assert EntityKey.OBSTACLE_AVOIDANCE_SELECT in spec.entities
    assert EntityKey.START_MOP_WASH_BUTTON in spec.entities
    assert EntityKey.STOP_DRY_BUTTON in spec.entities


async def test_d109_creates_all_eight_selects(hass, setup_integration):
    """X20 Max gets route, obstacle and dock selects on top of the base 3."""
    entity_ids = {s.entity_id for s in hass.states.async_all("select")}
    assert entity_ids == {
        "select.vacuum_mode",
        "select.vacuum_clean_times",
        "select.vacuum_mop_water_level",
        "select.vacuum_sweep_route",
        "select.vacuum_obstacle_avoidance",
        "select.vacuum_mop_washing_frequency",
        "select.vacuum_mop_washing_area_interval",
        "select.vacuum_mop_drying_time",
    }


async def test_d109_creates_the_dock_and_reset_buttons(hass, setup_integration):
    """One button per dock action, plus one life reset per consumable."""
    entity_ids = {s.entity_id for s in hass.states.async_all("button")}
    assert entity_ids == {
        "button.vacuum_collect_dust",
        "button.vacuum_wash_mop",
        "button.vacuum_stop_washing_mop",
        "button.vacuum_dry_mop",
        "button.vacuum_stop_drying_mop",
        "button.vacuum_reset_main_brush",
        "button.vacuum_reset_side_brush",
        "button.vacuum_reset_filter",
        "button.vacuum_reset_mop",
    }


@pytest.mark.parametrize(
    ("button", "address"),
    [
        ("reset_mop", ActionAddress(siid=9, aiid=1)),
        ("reset_main_brush", ActionAddress(siid=12, aiid=1)),
        ("reset_side_brush", ActionAddress(siid=13, aiid=1)),
        ("reset_filter", ActionAddress(siid=14, aiid=1)),
    ],
)
async def test_d109_reset_buttons_fire_the_consumable_actions(
    hass, setup_integration, mock_miot_device, button, address
):
    mock_miot_device.call_action.reset_mock()
    await hass.services.async_call(
        "button", "press", {"entity_id": f"button.vacuum_{button}"}, blocking=True
    )
    mock_miot_device.call_action.assert_called_once_with(address)


@pytest.mark.parametrize(
    ("entity_id", "expected"),
    [
        ("sensor.vacuum_mop_time_left", "68"),
        ("sensor.vacuum_main_brush_time_left", "213"),
        ("sensor.vacuum_side_brush_time_left", "180"),
        ("sensor.vacuum_filter_time_left", "105"),
    ],
)
async def test_d109_consumable_hours_left(hass, setup_integration, entity_id, expected):
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == expected
    assert state.attributes["unit_of_measurement"] == "h"


async def test_d109_consumable_hours_left_unknown_when_unreported(
    hass, setup_integration
):
    coordinator = setup_integration.runtime_data.coordinator
    coordinator.async_set_updated_data({**coordinator.data, "filter_time_left": None})
    await hass.async_block_till_done()
    assert hass.states.get("sensor.vacuum_filter_time_left").state == "unknown"


def test_d109_reads_the_consumable_hours_left_next_to_the_life_level():
    mapping = D109GL.property_mapping
    assert mapping[Property.MOP_TIME_LEFT] == {"siid": 9, "piid": 2}
    assert mapping[Property.MAIN_BRUSH_TIME_LEFT] == {"siid": 12, "piid": 2}
    assert mapping[Property.SIDE_BRUSH_TIME_LEFT] == {"siid": 13, "piid": 2}
    assert mapping[Property.FILTER_TIME_LEFT] == {"siid": 14, "piid": 2}


async def test_d109_mop_water_level_includes_off_option(hass, setup_integration):
    """X20 Max publishes 0 = Off for mop-water level (spec v2, siid 2 / piid 10)."""
    select = hass.states.get("select.vacuum_mop_water_level")
    assert select is not None
    assert "off" in select.attributes["options"]


async def test_d109_return_home_uses_vacuum_service(
    hass, setup_integration, mock_miot_device
):
    """X20 Max return-home is vacuum.return-to-charge (SIID 2 / aiid 3)."""
    mock_miot_device.call_action.reset_mock()
    await hass.services.async_call(
        "vacuum",
        "return_to_base",
        {"entity_id": "vacuum.vacuum"},
        blocking=True,
    )
    mock_miot_device.call_action.assert_any_call(ActionAddress(siid=2, aiid=3))


async def test_d109_continue_uses_vacuum_service(
    hass, setup_integration, mock_miot_device
):
    """X20 Max continue-sweep lives in the vacuum service (SIID 2 / aiid 8)."""
    coord = setup_integration.runtime_data.coordinator
    # status=4 (sweeping, not parked) -> 'start' triggers continue, not fresh start.
    coord.async_set_updated_data({**coord.data, "status": 4, "fault": 0})
    await hass.async_block_till_done()
    mock_miot_device.call_action.reset_mock()
    await hass.services.async_call(
        "vacuum",
        "start",
        {"entity_id": "vacuum.vacuum"},
        blocking=True,
    )
    mock_miot_device.call_action.assert_any_call(ActionAddress(siid=2, aiid=8))


async def test_d109_send_command_exposes_mop_wash_and_dry(hass, setup_integration):
    """The dock-only send_commands (mop-wash / dry) exist on the X20 Max whitelist."""
    spec = setup_integration.runtime_data.spec
    for cmd in (
        "start_mop_wash",
        "stop_mop_wash",
        "start_dry",
        "stop_dry",
        "start_only_sweep",
        "start_mop",
        "start_sweep_mop",
        "continue_sweep",
    ):
        assert cmd in spec.send_commands


async def test_d109_dust_arrest_button_hits_action(
    hass, setup_integration, mock_miot_device
):
    """Pressing the dust-arrest button targets the dock's start-dust-arrest action."""
    mock_miot_device.call_action.reset_mock()
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.vacuum_collect_dust"},
        blocking=True,
    )
    mock_miot_device.call_action.assert_any_call(ActionAddress(siid=2, aiid=18))


async def test_d109_clean_segments_uses_the_direct_room_sweep(
    hass, setup_integration, mock_miot_device
):
    """X20 Max room-clean fires start-vacuum-room-sweep directly (no cloud detour)."""
    client = setup_integration.runtime_data.client
    mock_miot_device.call_action.reset_mock()
    await client.async_clean_segments(["10", "28"])
    mock_miot_device.call_action.assert_any_call(
        ActionAddress(siid=2, aiid=16), [{"piid": 15, "value": "10,28"}]
    )


async def test_d109_parses_fault_ids_json_list(hass, setup_integration):
    """The X20 Max publishes a Fault Ids JSON list; coordinator extracts the code."""
    spec = setup_integration.runtime_data.spec

    def live(raw):
        return spec.live_fault_code({"fault_ids": raw})

    # Active fault (code 210009) at the head of the list.
    assert live(json.dumps({"ts": 1700000000, "fault": [210009]})) == 210009
    # [0] means no active fault.
    assert live(json.dumps({"fault": [0]})) == 0
    # Missing / unparseable -> None.
    assert live(None) is None
    assert live("not json") is None


async def test_d109_creates_the_setting_switches_and_numbers(hass, setup_integration):
    switches = {s.entity_id for s in hass.states.async_all("switch")}
    assert switches == {
        "switch.vacuum_carpet_boost",
        "switch.vacuum_resume_after_charging",
        "switch.vacuum_child_lock",
        "switch.vacuum_do_not_disturb",
        "switch.vacuum_mop_washing",
        "switch.vacuum_auto_empty_dust_bin",
        "switch.vacuum_auto_dry_mop",
    }
    numbers = {s.entity_id for s in hass.states.async_all("number")}
    assert numbers == {
        "number.vacuum_volume",
        "number.vacuum_mop_washing_time_interval",
    }


@pytest.mark.parametrize(
    ("entity_id", "state"),
    [
        ("switch.vacuum_carpet_boost", "off"),
        ("switch.vacuum_resume_after_charging", "on"),
        ("switch.vacuum_child_lock", "off"),
        ("switch.vacuum_do_not_disturb", "on"),
        ("switch.vacuum_mop_washing", "on"),
        ("switch.vacuum_auto_empty_dust_bin", "on"),
        ("switch.vacuum_auto_dry_mop", "on"),
        ("select.vacuum_mop_washing_frequency", "by_area"),
        ("select.vacuum_mop_washing_area_interval", "fifteen_square_meters"),
        ("select.vacuum_mop_drying_time", "3_hours"),
        ("number.vacuum_volume", "70"),
        ("number.vacuum_mop_washing_time_interval", "20"),
    ],
)
async def test_d109_settings_follow_the_device(
    hass, setup_integration, entity_id, state
):
    assert hass.states.get(entity_id).state == state


@pytest.mark.parametrize(
    ("entity_id", "service", "write"),
    [
        ("switch.vacuum_carpet_boost", "turn_on", ((2, 20), True)),
        ("switch.vacuum_resume_after_charging", "turn_off", ((2, 23), False)),
        ("switch.vacuum_child_lock", "turn_on", ((5, 1), True)),
        ("switch.vacuum_do_not_disturb", "turn_off", ((11, 1), False)),
        ("switch.vacuum_mop_washing", "turn_off", ((2, 28), False)),
        ("switch.vacuum_auto_empty_dust_bin", "turn_off", ((2, 32), False)),
        ("switch.vacuum_auto_dry_mop", "turn_off", ((2, 34), False)),
    ],
)
@pytest.mark.usefixtures("setup_integration")
async def test_d109_switches_write_a_bool(
    hass, mock_miot_device, entity_id, service, write
):
    from xiaomi_vacuum_sdk import PropertyAddress

    mock_miot_device.set_property.reset_mock()
    await hass.services.async_call(
        "switch", service, {"entity_id": entity_id}, blocking=True
    )
    (siid, piid), value = write
    mock_miot_device.set_property.assert_called_once_with(
        PropertyAddress(siid=siid, piid=piid), value
    )
    assert hass.states.get(entity_id).state == ("on" if value else "off")


@pytest.mark.parametrize(
    ("entity_id", "option", "write"),
    [
        ("select.vacuum_mop_washing_frequency", "by_time", ((2, 29), 2)),
        (
            "select.vacuum_mop_washing_area_interval",
            "eight_square_meters",
            ((2, 61), 2),
        ),
        ("select.vacuum_mop_drying_time", "4_hours", ((2, 31), 3)),
    ],
)
@pytest.mark.usefixtures("setup_integration")
async def test_d109_dock_selects_write_the_device_value(
    hass, mock_miot_device, entity_id, option, write
):
    from xiaomi_vacuum_sdk import PropertyAddress

    mock_miot_device.set_property.reset_mock()
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": entity_id, "option": option},
        blocking=True,
    )
    (siid, piid), value = write
    mock_miot_device.set_property.assert_called_once_with(
        PropertyAddress(siid=siid, piid=piid), value
    )
    assert hass.states.get(entity_id).state == option


async def test_d109_area_interval_options_are_ordered_by_area(hass, setup_integration):
    state = hass.states.get("select.vacuum_mop_washing_area_interval")
    assert state.attributes["options"] == [
        "five_square_meters",
        "eight_square_meters",
        "ten_square_meters",
        "fifteen_square_meters",
        "twenty_square_meters",
        "twenty_five_square_meters",
    ]


@pytest.mark.parametrize(
    ("entity_id", "key", "write"),
    [
        ("number.vacuum_volume", "volume", ((4, 2), 40)),
        (
            "number.vacuum_mop_washing_time_interval",
            "mop_wash_time_interval",
            ((2, 81), 30),
        ),
    ],
)
@pytest.mark.usefixtures("setup_integration")
async def test_d109_numbers_write_and_go_unknown(
    hass, mock_miot_device, entity_id, key, write
):
    from xiaomi_vacuum_sdk import PropertyAddress

    address, value = write
    await hass.services.async_call(
        "number", "set_value", {"entity_id": entity_id, "value": value}, blocking=True
    )
    mock_miot_device.set_property.assert_any_call(PropertyAddress(*address), value)
    assert float(hass.states.get(entity_id).state) == value
    (entry,) = hass.config_entries.async_entries(DOMAIN)
    coordinator = entry.runtime_data.coordinator
    coordinator.async_set_updated_data({**coordinator.data, key: None})
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "unknown"
