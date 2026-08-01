from __future__ import annotations

from unittest.mock import patch

import pytest
from miio import DeviceException
from miio.exceptions import RecoverableError

from custom_components.xiaomi_vacuum.api import (
    XiaomiVacuumApiClient,
    XiaomiVacuumApiClientCommunicationError,
    XiaomiVacuumApiClientError,
)
from custom_components.xiaomi_vacuum.api.client import _is_ack_timeout
from custom_components.xiaomi_vacuum.spec import _B108GL, _D109GL


def _client(hass, mock_miot_device, spec=_D109GL):
    return XiaomiVacuumApiClient(hass=hass, host="1.2.3.4", token="t" * 32, spec=spec)


def test_communication_error_is_api_error():
    assert issubclass(
        XiaomiVacuumApiClientCommunicationError, XiaomiVacuumApiClientError
    )


def test_init_passes_mapping_to_miot_device(hass, mock_miot_device):
    with patch("custom_components.xiaomi_vacuum.api.client.MiotDevice") as cls:
        XiaomiVacuumApiClient(hass=hass, host="1.2.3.4", token="t" * 32, spec=_D109GL)
        cls.assert_called_once_with(
            ip="1.2.3.4",
            token="t" * 32,
            mapping=_D109GL.property_mapping,
            timeout=10,
        )


async def test_async_get_info_returns_info(hass, mock_miot_device):
    info = await _client(hass, mock_miot_device).async_get_info()
    assert info.model == "xiaomi.vacuum.d109gl"


async def test_async_get_info_translates_device_exception(hass, mock_miot_device):
    mock_miot_device.info.side_effect = DeviceException("offline")
    with pytest.raises(XiaomiVacuumApiClientCommunicationError, match="Device error"):
        await _client(hass, mock_miot_device).async_get_info()


async def test_async_get_info_unexpected_exception(hass, mock_miot_device):
    mock_miot_device.info.side_effect = RuntimeError("boom")
    with pytest.raises(XiaomiVacuumApiClientError, match="Unexpected error"):
        await _client(hass, mock_miot_device).async_get_info()


async def test_async_get_state_indexes_by_siid_piid(hass, mock_miot_device):
    state = await _client(hass, mock_miot_device).async_get_state()
    assert state["status"] == 2
    assert state["battery_level"] == 99
    assert state["sweep_mop_type"] == 1


async def test_async_get_state_skips_failed_rows(hass, mock_miot_device):
    mock_miot_device.get_properties_for_mapping.return_value = [
        {"did": "x", "siid": 2, "piid": 2, "code": 0, "value": 4},
        {"did": "x", "siid": 3, "piid": 1, "code": -704, "value": None},
    ]
    state = await _client(hass, mock_miot_device).async_get_state()
    assert state["status"] == 4
    assert state["battery_level"] is None


async def test_async_start_calls_action(hass, mock_miot_device):
    await _client(hass, mock_miot_device).async_start()
    a = _D109GL.actions.start_sweep
    mock_miot_device.call_action_by.assert_called_with(a["siid"], a["aiid"])


async def test_async_pause_calls_action(hass, mock_miot_device):
    await _client(hass, mock_miot_device).async_pause()
    a = _D109GL.actions.pause_sweeping
    mock_miot_device.call_action_by.assert_called_with(a["siid"], a["aiid"])


async def test_async_stop_calls_action(hass, mock_miot_device):
    await _client(hass, mock_miot_device).async_stop()
    a = _D109GL.actions.stop_sweeping
    mock_miot_device.call_action_by.assert_called_with(a["siid"], a["aiid"])


async def test_async_return_home_calls_action(hass, mock_miot_device):
    await _client(hass, mock_miot_device).async_return_home()
    a = _D109GL.actions.return_home
    mock_miot_device.call_action_by.assert_called_with(a["siid"], a["aiid"])


async def test_async_locate_calls_action(hass, mock_miot_device):
    await _client(hass, mock_miot_device).async_locate()
    a = _D109GL.actions.identify
    mock_miot_device.call_action_by.assert_called_with(a["siid"], a["aiid"])


async def test_action_swallows_user_ack_timeout(hass, mock_miot_device):
    """A -9999 ack timeout is treated as accepted; no exception to HA."""
    recoverable = RecoverableError({"code": -9999, "message": "user ack timeout"})
    mock_miot_device.call_action_by.side_effect = DeviceException(
        "Unable to recover failed command"
    )
    mock_miot_device.call_action_by.side_effect.__cause__ = recoverable
    # Should not raise — the optimistic UI + refresh reconciles the real state.
    await _client(hass, mock_miot_device).async_start()


async def test_action_still_raises_non_ack_timeout_device_error(hass, mock_miot_device):
    """A genuine device error (not ack-timeout) still surfaces as a comm error."""
    mock_miot_device.call_action_by.side_effect = DeviceException("real failure")
    with pytest.raises(XiaomiVacuumApiClientCommunicationError):
        await _client(hass, mock_miot_device).async_start()


def test_is_ack_timeout_detects_minus_9999_in_cause_chain():
    recoverable = RecoverableError({"code": -9999, "message": "user ack timeout"})
    wrapped = DeviceException("Unable to recover failed command")
    wrapped.__cause__ = recoverable
    assert _is_ack_timeout(wrapped) is True


def test_is_ack_timeout_false_for_other_errors():
    recoverable = RecoverableError({"code": -7, "message": "other"})
    wrapped = DeviceException("Unable to recover failed command")
    wrapped.__cause__ = recoverable
    assert _is_ack_timeout(wrapped) is False
    assert _is_ack_timeout(DeviceException("plain")) is False


async def test_async_set_fan_speed_unknown_raises(hass, mock_miot_device):
    with pytest.raises(XiaomiVacuumApiClientError, match="Unknown fan speed"):
        await _client(hass, mock_miot_device).async_set_fan_speed("turbocharge")


async def test_async_set_fan_speed_known_writes_property(hass, mock_miot_device):
    await _client(hass, mock_miot_device).async_set_fan_speed("strong")
    prop = _D109GL.property_mapping["fan_speed"]
    mock_miot_device.set_property_by.assert_called_with(prop["siid"], prop["piid"], 3)


async def test_async_set_sweep_mop_type_unknown_raises(hass, mock_miot_device):
    with pytest.raises(XiaomiVacuumApiClientError, match="Unknown sweep_mop_type"):
        await _client(hass, mock_miot_device).async_set_sweep_mop_type("invalid")


async def test_async_set_sweep_mop_type_writes_property(hass, mock_miot_device):
    await _client(hass, mock_miot_device).async_set_sweep_mop_type("mop")
    prop = _D109GL.property_mapping["sweep_mop_type"]
    mock_miot_device.set_property_by.assert_called_with(prop["siid"], prop["piid"], 2)


async def test_async_set_property_unknown_name_raises(hass, mock_miot_device):
    with pytest.raises(XiaomiVacuumApiClientError, match="Unknown property"):
        await _client(hass, mock_miot_device).async_set_property("does_not_exist", 1)


async def test_async_set_property_writes_value(hass, mock_miot_device):
    await _client(hass, mock_miot_device).async_set_property("clean_times", 2)
    prop = _D109GL.property_mapping["clean_times"]
    mock_miot_device.set_property_by.assert_called_with(prop["siid"], prop["piid"], 2)


async def test_async_clean_segments_payload(hass, mock_miot_device):
    await _client(hass, mock_miot_device).async_clean_segments(["10", "28"])
    args = mock_miot_device.call_action_by.call_args.args
    a = _D109GL.actions.start_room_sweep
    assert args[0] == a["siid"]
    assert args[1] == a["aiid"]
    assert args[2] == [{"piid": a["in_piid"], "value": "10,28"}]


async def test_async_clean_segments_coerces_int_ids(hass, mock_miot_device):
    await _client(hass, mock_miot_device).async_clean_segments([10, 28])
    args = mock_miot_device.call_action_by.call_args.args
    assert args[2][0]["value"] == "10,28"


_ROOM_INFO_TABLE = (
    '{"version":2,"room_attrs":[["id","room_name","fan_level","water_level",'
    '"clean_mode","clean_times","mop_mode","on"],'
    '[3,"Living room",4,3,1,1,0,false],'
    '[4,"Kitchen",4,3,3,1,0,false],'
    '[5,"Hall",4,3,3,1,0,true]]}'
)


async def test_b108_clean_segments_uses_two_step_flow(hass, mock_miot_device_b108):
    """S20+ marks rooms via set-room-clean-configs then fires start-custom-sweep."""
    client = _client(hass, mock_miot_device_b108, spec=_B108GL)
    await client.async_clean_segments(["5"], room_information=_ROOM_INFO_TABLE)

    calls = mock_miot_device_b108.call_action_by.call_args_list
    # First: set-room-clean-configs (siid 2 / aiid 10) with the room_attrs JSON.
    set_call = calls[0].args
    assert set_call[0] == 2  # siid
    assert set_call[1] == 10  # aiid
    import json as _json

    payload = _json.loads(set_call[2][0])
    # Selected room (id 5) is emitted first; unselected keep their order.
    assert [r["id"] for r in payload["room_attrs"]] == [5, 3, 4]
    # Only the requested room (id 5) is flagged on=True.
    on_flags = {r["id"]: r["on"] for r in payload["room_attrs"]}
    assert on_flags == {3: False, 4: False, 5: True}

    # Second: start-custom-sweep (siid 6 / aiid 7) with empty input.
    start_call = calls[1].args
    assert start_call[0] == 6  # siid
    assert start_call[1] == 7  # aiid
    assert start_call[2] == []


async def test_b108_clean_segments_refuses_without_room_info(
    hass, mock_miot_device_b108
):
    """Without room_information the S20+ cannot build the config — refuse clearly."""
    client = _client(hass, mock_miot_device_b108, spec=_B108GL)
    with pytest.raises(XiaomiVacuumApiClientError, match="no room information"):
        await client.async_clean_segments(["5"], room_information=None)
    mock_miot_device_b108.call_action_by.assert_not_called()


def test_build_room_clean_config_marks_requested_rooms():
    from custom_components.xiaomi_vacuum.api.client import _build_room_clean_config

    rooms = _build_room_clean_config(_ROOM_INFO_TABLE, ["5"])
    assert {r["id"] for r in rooms} == {3, 4, 5}
    assert next(r for r in rooms if r["id"] == 5)["on"] is True
    assert all(r["on"] is False for r in rooms if r["id"] != 5)


def test_build_room_clean_config_preserves_requested_sequence():
    """Selected rooms come first, in the order the caller requested."""
    from custom_components.xiaomi_vacuum.api.client import _build_room_clean_config

    # Device order is [3,4,5]; request [5,3] (reversed for two of them).
    rooms = _build_room_clean_config(_ROOM_INFO_TABLE, ["5", "3"])
    selected = [r for r in rooms if r["on"]]
    others = [r for r in rooms if not r["on"]]
    # Selected rooms emitted in the requested order (5 then 3), before others.
    assert [r["id"] for r in selected] == [5, 3]
    assert [r["id"] for r in others] == [4]
    assert [r["id"] for r in rooms] == [5, 3, 4]


def test_build_room_clean_config_empty_when_no_room_info():
    from custom_components.xiaomi_vacuum.api.client import _build_room_clean_config

    assert _build_room_clean_config(None, ["5"]) == []
    assert _build_room_clean_config("", ["5"]) == []
    assert _build_room_clean_config("not json", ["5"]) == []


# Same room table as ``_ROOM_INFO_TABLE`` but with the header row published in
# mixed case (``Id`` / ``Room_Name``). A real device that doesn't emit the
# lower-case spelling must still resolve — both parsers read this payload.
_ROOM_INFO_TABLE_MIXED_CASE = (
    '{"version":2,"room_attrs":['
    '["Id","Room_Name","fan_level","water_level","clean_mode",'
    '"clean_times","mop_mode","on"],'
    '[3,"Living room",4,3,1,1,0,false],'
    '[4,"Kitchen",4,3,3,1,0,false],'
    '[5,"Hall",4,3,3,1,0,true]]}'
)


def test_build_room_clean_config_casefolds_header():
    """Header cells are case-folded, matching ``_rows_to_attrs`` in cleaner.py.

    Without this the per-room ``id`` lookup failed on every row and the config
    came back empty on a device that plainly published rooms.
    """
    from custom_components.xiaomi_vacuum.api.client import _build_room_clean_config

    rooms = _build_room_clean_config(_ROOM_INFO_TABLE_MIXED_CASE, ["5"])
    assert {r["id"] for r in rooms} == {3, 4, 5}
    assert next(r for r in rooms if r["id"] == 5)["on"] is True
    assert all(r["on"] is False for r in rooms if r["id"] != 5)


async def test_b108_clean_segments_routes_through_cloud_when_available(
    hass, mock_miot_device_b108
):
    """When a cloud session is attached, the S20+ room-clean uses the cloud path."""
    from unittest.mock import AsyncMock

    client = _client(hass, mock_miot_device_b108, spec=_B108GL)
    cloud = AsyncMock()
    # Successful cloud action responses carry code 0.
    cloud.async_call_action = AsyncMock(return_value={"code": 0, "message": "ok"})
    client.set_cloud(cloud)

    await client.async_clean_segments(["5"], room_information=_ROOM_INFO_TABLE)

    # Both actions go through the cloud (never touches the local device).
    mock_miot_device_b108.call_action_by.assert_not_called()
    assert cloud.async_call_action.await_count == 2
    first = cloud.async_call_action.await_args_list[0]
    second = cloud.async_call_action.await_args_list[1]
    # set-room-clean-configs (siid 2 / aiid 10) with the room_attrs payload.
    assert first.args[:2] == (2, 10)
    import json as _json

    payload = _json.loads(first.args[2][0])
    assert next(r for r in payload["room_attrs"] if r["id"] == 5)["on"] is True
    # start-custom-sweep (siid 6 / aiid 7) with empty input.
    assert second.args[:2] == (6, 7)
    assert second.args[2] == []


async def test_b108_clean_segments_cloud_reject_raises(hass, mock_miot_device_b108):
    """A non-zero device code from the cloud surfaces as a clear error."""
    from unittest.mock import AsyncMock

    client = _client(hass, mock_miot_device_b108, spec=_B108GL)
    cloud = AsyncMock()
    cloud.async_call_action = AsyncMock(
        return_value={"code": -7, "message": "invalid params"}
    )
    client.set_cloud(cloud)
    with pytest.raises(XiaomiVacuumApiClientError, match="rejected by device"):
        await client.async_clean_segments(["5"], room_information=_ROOM_INFO_TABLE)


async def test_b108_clean_segments_cloud_none_falls_back_to_local(
    hass, mock_miot_device_b108
):
    """A ``None`` cloud response means no transport — fall back to local miio.

    Regression guard: a ``None`` result previously skipped the ``code`` check and
    silently succeeded while nothing actually ran on the device (the optimistic
    UI had already reported the clean as started).
    """
    from unittest.mock import AsyncMock

    client = _client(hass, mock_miot_device_b108, spec=_B108GL)
    cloud = AsyncMock()
    # ``async_call_action`` returns None when the cloud has no active session or
    # no resolved device — i.e. the transport is unavailable, not success.
    cloud.async_call_action = AsyncMock(return_value=None)
    client.set_cloud(cloud)

    await client.async_clean_segments(["5"], room_information=_ROOM_INFO_TABLE)

    # Both actions fall through to the local miio transport.
    assert cloud.async_call_action.await_count == 2
    assert mock_miot_device_b108.call_action_by.call_count == 2


async def test_b108_return_home_uses_battery_service(hass, mock_miot_device_b108):
    """S20+ return-home hits the battery.start-charge action, not SIID 2/aiid 3."""
    await _client(hass, mock_miot_device_b108, spec=_B108GL).async_return_home()
    a = _B108GL.actions.return_home
    mock_miot_device_b108.call_action_by.assert_called_with(a["siid"], a["aiid"])
    assert a == {"siid": 3, "aiid": 1}


async def test_b108_continue_uses_vacuum_extend_service(hass, mock_miot_device_b108):
    """S20+ continue-sweep lives on the vacuum-extend service (SIID 6 / aiid 1)."""
    await _client(hass, mock_miot_device_b108, spec=_B108GL).async_continue()
    a = _B108GL.actions.continue_sweep
    assert a == {"siid": 6, "aiid": 1}
    mock_miot_device_b108.call_action_by.assert_called_with(a["siid"], a["aiid"])


async def test_b108_dust_arrest_raises(hass, mock_miot_device_b108):
    """S20+ has no auto-dust dock; the action must surface a clear error."""
    with pytest.raises(XiaomiVacuumApiClientError, match="no dust-arrest"):
        await _client(
            hass, mock_miot_device_b108, spec=_B108GL
        ).async_start_dust_arrest()


async def test_run_propagates_device_exception_as_communication_error(
    hass, mock_miot_device
):
    mock_miot_device.call_action_by.side_effect = DeviceException("timeout")
    with pytest.raises(XiaomiVacuumApiClientCommunicationError):
        await _client(hass, mock_miot_device).async_start()


async def test_run_propagates_unexpected_as_api_error(hass, mock_miot_device):
    mock_miot_device.call_action_by.side_effect = ValueError("bad")
    with pytest.raises(XiaomiVacuumApiClientError, match="Unexpected"):
        await _client(hass, mock_miot_device).async_start()
