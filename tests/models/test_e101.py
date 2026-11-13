"""End-to-end behaviour for the S40C (xiaomi.vacuum.e101gb) model.

The S40C shares the S40 Pro's vacuum-service layout and ships with a plain
charging dock, so it gets the same entities and the same room and rectangle
commands. It does not inherit the S40 Pro's ignored and notice fault codes:
those were observed on a different unit.
"""

from __future__ import annotations

import json

import pytest
from homeassistant.components.vacuum import Segment
from homeassistant.components.vacuum.const import VacuumActivity
from homeassistant.config_entries import ConfigEntryState
from xiaomi_vacuum_sdk import ActionAddress

from custom_components.xiaomi_vacuum.const import DOMAIN
from custom_components.xiaomi_vacuum.spec import (
    E101GB,
    DirectRoomSweep,
    EntityKey,
    FaultIdsReading,
    Property,
)

_MODEL = "xiaomi.vacuum.e101gb"


async def test_e101_setup_loads(hass, setup_model):
    entry, _device = await setup_model(_MODEL)
    assert entry.state == ConfigEntryState.LOADED


async def test_e101_picks_the_right_spec(hass, setup_model):
    entry, _device = await setup_model(_MODEL)
    spec = entry.runtime_data.spec
    assert spec is E101GB
    assert spec.model == _MODEL
    assert spec.name == "Xiaomi Robot Vacuum S40C"
    assert isinstance(spec.fault_reading, FaultIdsReading)
    assert isinstance(spec.room_cleaning, DirectRoomSweep)
    assert spec.ignored_fault_codes == frozenset()
    assert spec.notice_fault_codes == frozenset()
    assert EntityKey.DUST_ARREST_BUTTON not in spec.entities
    assert spec.actions.start_zone_sweep == {"siid": 2, "aiid": 37, "in_piid": 12}
    assert spec.actions.start_user_define_sweep is None


async def test_e101_raises_no_unsupported_model_repair(hass, setup_model):
    from homeassistant.helpers import issue_registry as ir

    entry, _device = await setup_model(_MODEL)
    registry = ir.async_get(hass)
    issue_id = f"unsupported_model_{entry.entry_id}"
    assert registry.async_get_issue(DOMAIN, issue_id) is None


async def test_e101_has_only_the_consumable_reset_buttons(hass, setup_model):
    """Plain charging dock: no station buttons, only the life resets."""
    _entry, _device = await setup_model(_MODEL)
    entity_ids = {state.entity_id for state in hass.states.async_all("button")}
    assert entity_ids == {
        "button.s40c_reset_main_brush",
        "button.s40c_reset_side_brush",
        "button.s40c_reset_filter",
        "button.s40c_reset_mop",
    }


async def test_e101_has_no_dock_actions(hass, setup_model):
    entry, _device = await setup_model(_MODEL)
    actions = entry.runtime_data.spec.actions
    assert actions.start_dust_arrest is None
    assert actions.start_mop_wash is None
    assert actions.start_dry is None
    assert actions.stop_mop_wash is None
    assert actions.stop_dry is None


async def test_e101_send_command_has_no_dock_commands(hass, setup_model):
    entry, _device = await setup_model(_MODEL)
    assert set(entry.runtime_data.spec.send_commands) == {
        "start_only_sweep",
        "start_mop",
        "start_sweep_mop",
        "continue_sweep",
    }


async def test_e101_status_table_covers_the_published_codes(hass, setup_model):
    """The released spec publishes codes 1-24, the same set as the S40 Pro."""
    entry, _device = await setup_model(_MODEL)
    spec = entry.runtime_data.spec
    assert set(spec.status) == set(range(1, 25))
    assert VacuumActivity.ERROR not in spec.status_to_activity.values()
    assert spec.status_to_activity[2] is VacuumActivity.DOCKED


async def test_e101_reads_the_s40_pro_property_addresses(hass, setup_model):
    _entry, _device = await setup_model(_MODEL)
    mapping = E101GB.property_mapping
    assert mapping[Property.STATUS] == {"siid": 2, "piid": 2}
    assert mapping[Property.FAULT_IDS] == {"siid": 2, "piid": 66}
    assert mapping[Property.ROOM_INFORMATION] == {"siid": 2, "piid": 16}
    assert mapping[Property.BATTERY_LEVEL] == {"siid": 3, "piid": 1}
    assert mapping[Property.MAP_OBJ_NAME] == {"siid": 10, "piid": 1}
    assert Property.USER_DEFINE_SWEEP_CONFIG not in mapping


async def test_e101_parses_the_room_payload_a_real_device_publishes(hass, setup_model):
    """Named rooms from the physical unit; blank names stay out of the list."""
    entry, _device = await setup_model(_MODEL)
    entity = hass.data["entity_components"]["vacuum"].get_entity("vacuum.s40c")
    assert await entity.async_get_segments() == [
        Segment(id="3", name="Спальня"),
        Segment(id="4", name="Кабинет"),
        Segment(id="5", name="Кухня"),
        Segment(id="9", name="Прихожая"),
    ]
    assert entry.runtime_data.spec.room_cleaning == DirectRoomSweep(
        {"siid": 2, "aiid": 16, "in_piid": 15}
    )


async def test_e101_clean_segments_uses_the_direct_room_sweep(hass, setup_model):
    entry, device = await setup_model(_MODEL)
    device.call_action.reset_mock()
    await entry.runtime_data.client.async_clean_segments(["5", "9"])
    device.call_action.assert_any_call(
        ActionAddress(siid=2, aiid=16), [{"piid": 15, "value": "5,9"}]
    )


async def test_e101_clean_zone_uses_the_s40_pro_rectangle_payload(hass, setup_model):
    """Same 2/37 block list as the S40 Pro. Not yet started on a physical S40C."""
    _entry, device = await setup_model(_MODEL)
    device.call_action.reset_mock()
    device.set_property.reset_mock()
    await hass.services.async_call(
        DOMAIN,
        "clean_zone",
        {"entity_id": "vacuum.s40c", "zones": [[890, 750, 260, 250]], "repeats": 1},
        blocking=True,
    )
    device.set_property.assert_called_once()
    address, payload = device.call_action.call_args.args
    assert address == ActionAddress(siid=2, aiid=37)
    assert json.loads(payload[0]["value"]) == [
        {"blocks_region": [260, 750, 260, 250, 890, 250, 890, 750], "blocks_attr": 0}
    ]


@pytest.mark.parametrize("code", [100027, 210005, 210020])
async def test_e101_does_not_inherit_the_s40_pro_fault_exceptions(
    hass, setup_model, code
):
    """Codes the S40 Pro hides were not published by this unit, so they count."""
    entry, _device = await setup_model(_MODEL)
    coordinator = entry.runtime_data.coordinator
    coordinator.async_set_updated_data({**coordinator.data, "status": 2, "fault": code})
    await hass.async_block_till_done()
    assert hass.states.get("vacuum.s40c").state == "error"
    assert hass.states.get("sensor.s40c_error_code").state == str(code)
