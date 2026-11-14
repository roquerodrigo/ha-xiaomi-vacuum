"""End-to-end behaviour for the S40 Pro (xiaomi.vacuum.ov71gl) model.

The S40 Pro shares the X20 Max's vacuum-service layout, so it must get the
sweep-route / obstacle-avoidance selects and route room cleaning through the
direct start-vacuum-room-sweep action. It ships with a plain charging dock,
so despite the spec template listing dock actions it must get no dust-arrest
button and no mop-wash / dry send_commands. Its status table adds the three
station-assisted washing codes (22-24). Taking the water tank or dust bin
out is a maintenance notice, not a fault: the vacuum must not go to ERROR.
"""

from __future__ import annotations

import pytest
from homeassistant.components.vacuum.const import VacuumActivity
from homeassistant.config_entries import ConfigEntryState
from xiaomi_vacuum_sdk import ActionAddress

from custom_components.xiaomi_vacuum.spec import (
    OV71GL,
    DirectRoomSweep,
    EntityKey,
    FaultIdsReading,
    Property,
)

#: `room-information` (2/16) exactly as a physical S40 Pro published it
#: (firmware 4.5.8_0053), accents and all.
REAL_ROOM_INFORMATION = (
    '{"rooms":[{"id":3,"name":"Salle à manger"},{"id":4,"name":"Cuisine"},'
    '{"id":5,"name":"Salon"},{"id":6,"name":"Entrée"}],"map_uid":1}'
)


async def test_ov71_setup_loads(hass, setup_integration_ov71):
    assert setup_integration_ov71.state == ConfigEntryState.LOADED


async def test_ov71_picks_the_right_spec(hass, setup_integration_ov71):
    spec = setup_integration_ov71.runtime_data.spec
    assert spec is OV71GL
    assert spec.model == "xiaomi.vacuum.ov71gl"
    assert isinstance(spec.fault_reading, FaultIdsReading)
    assert isinstance(spec.room_cleaning, DirectRoomSweep)
    assert EntityKey.SWEEP_ROUTE_SELECT in spec.entities
    assert EntityKey.OBSTACLE_AVOIDANCE_SELECT in spec.entities
    assert EntityKey.DUST_ARREST_BUTTON not in spec.entities


async def test_ov71_raises_no_unsupported_model_repair(hass, setup_integration_ov71):
    from homeassistant.helpers import issue_registry as ir

    from custom_components.xiaomi_vacuum.const import DOMAIN

    registry = ir.async_get(hass)
    issue_id = f"unsupported_model_{setup_integration_ov71.entry_id}"
    assert registry.async_get_issue(DOMAIN, issue_id) is None


async def test_ov71_creates_all_six_selects(hass, setup_integration_ov71):
    states = hass.states.async_all("select")
    entity_ids = {s.entity_id for s in states}
    assert len(states) == 6
    assert "select.s40_pro_carpet_cleaning" in entity_ids
    assert "select.s40_pro_sweep_route" in entity_ids
    assert "select.s40_pro_obstacle_avoidance" in entity_ids


async def test_ov71_has_the_robot_settings_but_no_dock_settings(
    hass, setup_integration_ov71
):
    """Settings its own spec publishes are kept; the plain dock gets none."""
    switches = {s.entity_id for s in hass.states.async_all("switch")}
    assert switches == {
        "switch.s40_pro_carpet_boost",
        "switch.s40_pro_resume_after_charging",
        "switch.s40_pro_child_lock",
        "switch.s40_pro_do_not_disturb",
    }
    numbers = {s.entity_id for s in hass.states.async_all("number")}
    assert numbers == {"number.s40_pro_volume"}
    for key in (
        EntityKey.MOP_WASH_SWITCH,
        EntityKey.MOP_WASH_FREQUENCY_SELECT,
        EntityKey.MOP_WASH_AREA_INTERVAL_SELECT,
        EntityKey.MOP_WASH_TIME_INTERVAL_NUMBER,
        EntityKey.MOP_DRYING_TIME_SELECT,
        EntityKey.AUTO_DUST_COLLECTION_SWITCH,
        EntityKey.AUTO_MOP_DRYING_SWITCH,
        EntityKey.MOP_WASH_WATER_MODE_SELECT,
        EntityKey.MOP_WASH_TEMPERATURE_SELECT,
        EntityKey.DUST_COLLECTION_FREQUENCY_SELECT,
    ):
        assert key not in OV71GL.entities


async def test_ov71_has_only_the_consumable_reset_buttons(hass, setup_integration_ov71):
    """Plain charging dock: no dock buttons, only the life resets."""
    entity_ids = {s.entity_id for s in hass.states.async_all("button")}
    assert entity_ids == {
        "button.s40_pro_reset_main_brush",
        "button.s40_pro_reset_side_brush",
        "button.s40_pro_reset_filter",
        "button.s40_pro_reset_mop",
    }


async def test_ov71_inherits_the_consumable_hours_left(hass, setup_integration_ov71):
    """Its own spec publishes them at the X20 Max's addresses."""
    for consumable in ("mop", "main_brush", "side_brush", "filter"):
        state = hass.states.get(f"sensor.s40_pro_{consumable}_time_left")
        assert state is not None
        assert state.state not in ("unknown", "unavailable")
    assert OV71GL.actions.reset_mop == {"siid": 9, "aiid": 1}
    assert OV71GL.actions.reset_filter == {"siid": 14, "aiid": 1}


async def test_ov71_has_no_dock_actions(hass, setup_integration_ov71):
    actions = setup_integration_ov71.runtime_data.spec.actions
    assert actions.start_dust_arrest is None
    assert actions.start_mop_wash is None
    assert actions.start_dry is None
    assert actions.stop_mop_wash is None
    assert actions.stop_dry is None


async def test_ov71_send_command_has_no_dock_commands(hass, setup_integration_ov71):
    spec = setup_integration_ov71.runtime_data.spec
    assert set(spec.send_commands) == {
        "start_only_sweep",
        "start_mop",
        "start_sweep_mop",
        "continue_sweep",
    }


async def test_ov71_clean_times_offers_three_repetitions(hass, setup_integration_ov71):
    select = hass.states.get("select.s40_pro_clean_times")
    assert select is not None
    assert select.attributes["options"] == ["one_time", "two_times", "three_times"]


async def test_ov71_status_table_covers_the_published_codes(
    hass, setup_integration_ov71
):
    """Every status value of the published spec (1-24) maps to a non-error activity."""
    spec = setup_integration_ov71.runtime_data.spec
    assert set(spec.status) == set(range(1, 25))
    assert VacuumActivity.ERROR not in spec.status_to_activity.values()
    assert spec.idle_statuses == frozenset({1, 2, 9})
    assert spec.status_to_activity[22] is VacuumActivity.DOCKED
    assert spec.status_to_activity[23] is VacuumActivity.DOCKED
    assert spec.status_to_activity[24] is VacuumActivity.RETURNING


async def test_ov71_station_assisted_status_shows_as_docked(
    hass, setup_integration_ov71
):
    """The fixture reports status 22, a rinse at the dock; the vacuum is docked."""
    state = hass.states.get("vacuum.s40_pro")
    assert state is not None
    assert state.state == "docked"
    status = hass.states.get("sensor.s40_pro_status")
    assert status is not None
    assert status.state == "station_assisting_cleaning"


async def test_ov71_return_home_uses_vacuum_service(
    hass, setup_integration_ov71, mock_miot_device_ov71
):
    mock_miot_device_ov71.call_action.reset_mock()
    await hass.services.async_call(
        "vacuum",
        "return_to_base",
        {"entity_id": "vacuum.s40_pro"},
        blocking=True,
    )
    mock_miot_device_ov71.call_action.assert_any_call(ActionAddress(siid=2, aiid=3))


async def test_ov71_locate_uses_identify_service(
    hass, setup_integration_ov71, mock_miot_device_ov71
):
    mock_miot_device_ov71.call_action.reset_mock()
    await hass.services.async_call(
        "vacuum",
        "locate",
        {"entity_id": "vacuum.s40_pro"},
        blocking=True,
    )
    mock_miot_device_ov71.call_action.assert_any_call(ActionAddress(siid=6, aiid=1))


async def test_ov71_clean_segments_uses_the_direct_room_sweep(
    hass, setup_integration_ov71, mock_miot_device_ov71
):
    """Room clean fires start-vacuum-room-sweep (2/16) with the ids on piid 15."""
    client = setup_integration_ov71.runtime_data.client
    mock_miot_device_ov71.call_action.reset_mock()
    await client.async_clean_segments(["10", "28"])
    mock_miot_device_ov71.call_action.assert_any_call(
        ActionAddress(siid=2, aiid=16), [{"piid": 15, "value": "10,28"}]
    )


async def test_ov71_reads_its_own_property_addresses(hass, setup_integration_ov71):
    """Pin the S40 Pro's own addresses, which happen to match the X20 Max layout."""
    mapping = OV71GL.property_mapping
    assert mapping[Property.STATUS] == {"siid": 2, "piid": 2}
    assert mapping[Property.FAULT_IDS] == {"siid": 2, "piid": 66}
    assert mapping[Property.ROOM_INFORMATION] == {"siid": 2, "piid": 16}
    assert mapping[Property.BATTERY_LEVEL] == {"siid": 3, "piid": 1}
    assert mapping[Property.MAP_OBJ_NAME] == {"siid": 10, "piid": 1}


async def test_ov71_parses_the_room_payload_a_real_device_publishes(
    hass, setup_integration_ov71
):
    """Accented room names survive the round trip into HA segments."""
    from homeassistant.components.vacuum import Segment

    coord = setup_integration_ov71.runtime_data.coordinator
    coord.async_set_updated_data(
        {**coord.data, "room_information": REAL_ROOM_INFORMATION}
    )
    await hass.async_block_till_done()
    entity = hass.data["entity_components"]["vacuum"].get_entity("vacuum.s40_pro")
    assert await entity.async_get_segments() == [
        Segment(id="3", name="Salle à manger"),
        Segment(id="4", name="Cuisine"),
        Segment(id="5", name="Salon"),
        Segment(id="6", name="Entrée"),
    ]


@pytest.mark.parametrize("code", [210005, 210020])
async def test_ov71_maintenance_notice_does_not_force_error(
    hass, setup_integration_ov71, code
):
    """Dust bin / water tank out: vacuum stays docked, sensors still show it."""
    coord = setup_integration_ov71.runtime_data.coordinator
    coord.async_set_updated_data({**coord.data, "status": 9, "fault": code})
    await hass.async_block_till_done()
    assert hass.states.get("vacuum.s40_pro").state == "docked"
    assert hass.states.get("sensor.s40_pro_error_code").state == str(code)


async def test_ov71_real_fault_still_forces_error(hass, setup_integration_ov71):
    coord = setup_integration_ov71.runtime_data.coordinator
    coord.async_set_updated_data({**coord.data, "status": 9, "fault": 210009})
    await hass.async_block_till_done()
    assert hass.states.get("vacuum.s40_pro").state == "error"
