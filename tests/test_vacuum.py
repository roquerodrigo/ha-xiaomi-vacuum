from __future__ import annotations

import json

import pytest
from homeassistant.components.vacuum import VacuumActivity

from custom_components.xiaomi_vacuum.const import (
    DOMAIN,
    STATUS_TO_ACTIVITY,
)
from custom_components.xiaomi_vacuum.vacuum import _parse_segments


@pytest.mark.parametrize(("status_code", "expected"), list(STATUS_TO_ACTIVITY.items()))
def test_status_to_activity_mapping(status_code, expected):
    assert isinstance(expected, VacuumActivity)


async def test_vacuum_activity_docked(hass, setup_integration):
    state = hass.states.get("vacuum.aspirador")
    assert state is not None
    # status:2 (Charging) -> DOCKED
    assert state.state == "docked"


async def test_vacuum_fan_speed(hass, setup_integration):
    state = hass.states.get("vacuum.aspirador")
    # fan_speed:2 -> "basic"
    assert state.attributes["fan_speed"] == "basic"


async def test_vacuum_extra_attributes(hass, setup_integration):
    state = hass.states.get("vacuum.aspirador")
    extras = state.attributes[DOMAIN]
    assert extras["status"] == "charging"
    assert extras["charging_state"] == "charging"
    assert extras["cleaning_area"] == 200


async def test_vacuum_unknown_activity_when_no_status(hass, setup_integration):
    state = hass.states.get("vacuum.aspirador")
    # current parsed state has status=2, force a new state without it
    coord = setup_integration.runtime_data.coordinator
    coord.async_set_updated_data({**coord.data, "status": None})
    await hass.async_block_till_done()
    state = hass.states.get("vacuum.aspirador")
    assert state.state in ("unknown", "unavailable")


async def test_vacuum_start_calls_api(hass, setup_integration, mock_miot_device):
    mock_miot_device.call_action_by.reset_mock()
    await hass.services.async_call(
        "vacuum",
        "start",
        {"entity_id": "vacuum.aspirador"},
        blocking=True,
    )
    assert mock_miot_device.call_action_by.called


async def test_vacuum_stop_calls_api(hass, setup_integration, mock_miot_device):
    mock_miot_device.call_action_by.reset_mock()
    await hass.services.async_call(
        "vacuum", "stop", {"entity_id": "vacuum.aspirador"}, blocking=True
    )
    assert mock_miot_device.call_action_by.called


async def test_vacuum_pause_calls_api(hass, setup_integration, mock_miot_device):
    mock_miot_device.call_action_by.reset_mock()
    await hass.services.async_call(
        "vacuum", "pause", {"entity_id": "vacuum.aspirador"}, blocking=True
    )
    assert mock_miot_device.call_action_by.called


async def test_vacuum_return_to_base(hass, setup_integration, mock_miot_device):
    mock_miot_device.call_action_by.reset_mock()
    await hass.services.async_call(
        "vacuum", "return_to_base", {"entity_id": "vacuum.aspirador"}, blocking=True
    )
    assert mock_miot_device.call_action_by.called


async def test_vacuum_locate(hass, setup_integration, mock_miot_device):
    mock_miot_device.call_action_by.reset_mock()
    await hass.services.async_call(
        "vacuum", "locate", {"entity_id": "vacuum.aspirador"}, blocking=True
    )
    assert mock_miot_device.call_action_by.called


async def test_vacuum_set_fan_speed(hass, setup_integration, mock_miot_device):
    mock_miot_device.set_property_by.reset_mock()
    await hass.services.async_call(
        "vacuum",
        "set_fan_speed",
        {"entity_id": "vacuum.aspirador", "fan_speed": "strong"},
        blocking=True,
    )
    assert mock_miot_device.set_property_by.called


async def test_parse_segments_with_rooms_dict(sample_room_info):
    segs = _parse_segments(sample_room_info)
    assert len(segs) == 2
    assert {s.id for s in segs} == {"10", "28"}


def test_parse_segments_empty_returns_empty():
    assert _parse_segments(None) == []
    assert _parse_segments("") == []


def test_parse_segments_invalid_json_returns_empty():
    assert _parse_segments("not json") == []


def test_parse_segments_list_payload():
    raw = json.dumps([{"id": 1, "name": "A"}, {"id": 2, "name": "B"}])
    segs = _parse_segments(raw)
    assert len(segs) == 2


def test_parse_segments_skips_entries_missing_id_or_name():
    raw = json.dumps([{"id": 1}, {"name": "x"}, {"id": 3, "name": "C"}])
    segs = _parse_segments(raw)
    assert len(segs) == 1
    assert segs[0].id == "3"


def test_parse_segments_alt_key_names():
    raw = json.dumps([{"roomId": 5, "roomName": "Quarto"}])
    segs = _parse_segments(raw)
    assert len(segs) == 1
    assert segs[0].id == "5"
    assert segs[0].name == "Quarto"


async def test_async_get_segments_via_entity(hass, setup_integration):
    coord = setup_integration.runtime_data.coordinator
    from custom_components.xiaomi_vacuum.vacuum import XiaomiVacuum

    entity = XiaomiVacuum(coordinator=coord)
    segs = await entity.async_get_segments()
    assert len(segs) == 2


async def test_async_clean_segments_via_entity(
    hass, setup_integration, mock_miot_device
):
    mock_miot_device.call_action_by.reset_mock()
    coord = setup_integration.runtime_data.coordinator
    from custom_components.xiaomi_vacuum.vacuum import XiaomiVacuum

    entity = XiaomiVacuum(coordinator=coord)
    entity.hass = hass
    await entity.async_clean_segments(["10", "28"])
    assert mock_miot_device.call_action_by.called
