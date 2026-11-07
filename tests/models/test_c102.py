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
from xiaomi_vacuum_sdk import ActionAddress

# Top-level import triggers custom-component loading in the HA pytest harness.
from custom_components.xiaomi_vacuum.const import DOMAIN  # noqa: F401
from custom_components.xiaomi_vacuum.spec import C102GL, Capability, EntityKey

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
    assert spec.fault_kind == "simple"
    assert spec.capabilities == frozenset({Capability.DUST_ARREST})


async def test_c102_creates_only_the_mop_water_level_select(
    hass, setup_integration_c102
):
    """Mode and clean times live in a packed Dreame bitfield: no selects yet."""
    states = hass.states.async_all("select")
    assert [s.entity_id for s in states] == ["select.x20_plus_mop_water_level"]
    assert states[0].attributes["options"] == ["level_1", "level_2", "level_3"]
    assert states[0].state == "level_2"


async def test_c102_creates_the_dust_arrest_button(hass, setup_integration_c102):
    buttons = hass.states.async_all("button")
    assert [b.entity_id for b in buttons] == ["button.x20_plus_collect_dust"]


async def test_c102_has_no_map_entity(hass, setup_integration_c102):
    """The Dreame map format cannot be rendered yet, so no empty map entity."""
    assert hass.states.async_all("image") == []


async def test_c102_cloud_session_skips_the_map_renderer(
    hass, setup_integration_c102_with_cloud, mock_cloud
):
    entry = setup_integration_c102_with_cloud
    assert entry.state == ConfigEntryState.LOADED
    assert entry.runtime_data.map_coordinator is None
    assert entry.runtime_data.coordinator.cloud is mock_cloud
    assert hass.states.async_all("image") == []


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
    setup_integration_c102.runtime_data.spec = replace(
        spec, actions=replace(spec.actions, start_segment_clean=None)
    )
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


async def test_c102_rooms_come_from_the_dreame_map(
    hass, setup_integration_c102_with_cloud, mock_cloud, dreame_map, dreame_name
):
    """Unnamed segments (doorways the lidar mapped) are left out."""
    mock_cloud.async_get_map_bytes.return_value = dreame_map(
        {
            "5": {"name": dreame_name("Escritório"), "type": 0},
            "1": {"name": dreame_name("Living room"), "type": 0},
            "4": {"type": 0},
        }
    )
    segments = await _vacuum(hass).async_get_segments()
    mock_cloud.async_get_map_bytes.assert_awaited_with("1234/567/map.bin")
    assert [(s.id, s.name) for s in segments] == [
        ("1", "Living room"),
        ("5", "Escritório"),
    ]


async def test_c102_rooms_survive_a_cloud_failure(
    hass, setup_integration_c102_with_cloud, mock_cloud, dreame_map, dreame_name
):
    from custom_components.xiaomi_vacuum.cloud import XiaomiCloudConnectionError

    mock_cloud.async_get_map_bytes.return_value = dreame_map(
        {"1": {"name": dreame_name("Living room")}}
    )
    vacuum = _vacuum(hass)
    first = await vacuum.async_get_segments()
    mock_cloud.async_get_map_bytes.side_effect = XiaomiCloudConnectionError("down")
    assert await vacuum.async_get_segments() == first
    mock_cloud.async_get_map_bytes.side_effect = None
    mock_cloud.async_get_map_bytes.return_value = None
    assert await vacuum.async_get_segments() == first
    mock_cloud.async_get_map_bytes.return_value = b"garbage"
    assert await vacuum.async_get_segments() == first


async def test_c102_rooms_need_the_cloud(hass, setup_integration_c102):
    assert await _vacuum(hass).async_get_segments() == []


async def test_c102_rooms_need_the_map_object(
    hass, setup_integration_c102_with_cloud, mock_cloud
):
    await _report(hass, setup_integration_c102_with_cloud, map_obj_name=None)
    assert await _vacuum(hass).async_get_segments() == []
    mock_cloud.async_get_map_bytes.assert_not_awaited()


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
    """The map object is mapped for the rooms, but the Dreame map is not drawn."""
    from custom_components.xiaomi_vacuum.spec import Property

    assert Property.MAP_OBJ_NAME in C102GL.property_mapping
    entities = C102GL.entities
    assert EntityKey.MOP_PAD_SENSOR in entities
    assert EntityKey.MOP_WATER_LEVEL_SELECT in entities
    assert EntityKey.DUST_ARREST_BUTTON in entities
    for key in (
        EntityKey.MAP_IMAGE,
        EntityKey.SWEEP_MOP_TYPE_SELECT,
        EntityKey.CLEAN_TIMES_SELECT,
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
