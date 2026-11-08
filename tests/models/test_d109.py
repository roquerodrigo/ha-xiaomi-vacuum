"""End-to-end behaviour for the X20 Max (xiaomi.vacuum.d109gl) model.

Mirror of ``test_b108.py``: the X20 Max must get the sweep-route /
obstacle-avoidance selects and the dust-arrest button (it has that hardware),
its return-home must hit the vacuum service (SIID 2 / aiid 3, not the battery
service like the S20+), and the live ``Fault Ids`` JSON list must be parsed.
"""

from __future__ import annotations

import json

from homeassistant.config_entries import ConfigEntryState
from xiaomi_vacuum_sdk import ActionAddress

# Top-level import triggers custom-component loading in the HA pytest harness;
# without it `from custom_components.xiaomi_vacuum...` inside tests fails with
# AttributeError until another test file imports the package first.
from custom_components.xiaomi_vacuum.const import DOMAIN  # noqa: F401
from custom_components.xiaomi_vacuum.spec import EntityKey, FaultIdsReading


async def test_d109_setup_loads(hass, setup_integration):
    assert setup_integration.state == ConfigEntryState.LOADED


async def test_d109_picks_the_right_spec(hass, setup_integration):

    spec = setup_integration.runtime_data.spec
    assert spec.model == "xiaomi.vacuum.d109gl"
    assert isinstance(spec.fault_reading, FaultIdsReading)
    assert EntityKey.DUST_ARREST_BUTTON in spec.entities
    assert EntityKey.SWEEP_ROUTE_SELECT in spec.entities
    assert EntityKey.OBSTACLE_AVOIDANCE_SELECT in spec.entities
    # Mop-wash / dry dock actions exist on the X20 Max but are not a gating
    # capability (no entity is created from them); they're exposed only via
    # send_commands and asserted in test_d109_send_command_exposes_mop_wash_and_dry.


async def test_d109_creates_all_five_selects(hass, setup_integration):
    """X20 Max gets sweep-route + obstacle-avoidance selects on top of the base 3."""
    states = hass.states.async_all("select")
    entity_ids = {s.entity_id for s in states}
    assert len(states) == 5
    assert "select.vacuum_sweep_route" in entity_ids
    assert "select.vacuum_obstacle_avoidance" in entity_ids


async def test_d109_creates_the_dock_buttons(hass, setup_integration):
    """The auto-empty and auto-wash dock get one button per dock action."""
    entity_ids = {s.entity_id for s in hass.states.async_all("button")}
    assert entity_ids == {
        "button.vacuum_collect_dust",
        "button.vacuum_wash_mop",
        "button.vacuum_stop_washing_mop",
        "button.vacuum_dry_mop",
        "button.vacuum_stop_drying_mop",
    }


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


async def test_d109_clean_segments_uses_direct_strategy(
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
