from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from xiaomi_vacuum_sdk import (
    ActionAddress,
    MiotAckTimeoutError,
    MiotConnectionError,
    MiotDeviceError,
    PropertyAddress,
)

from custom_components.xiaomi_vacuum.api import (
    XiaomiVacuumApiClient,
    XiaomiVacuumApiClientCommunicationError,
    XiaomiVacuumApiClientError,
)
from custom_components.xiaomi_vacuum.api.client import _build_room_clean_config
from custom_components.xiaomi_vacuum.spec import B108GL, D109GL


def _client(mock_miot_device, spec=D109GL):
    return XiaomiVacuumApiClient(host="1.2.3.4", token="t" * 32, spec=spec)


def _action_address(action) -> ActionAddress:
    return ActionAddress(siid=action["siid"], aiid=action["aiid"])


def test_communication_error_is_api_error():
    assert issubclass(
        XiaomiVacuumApiClientCommunicationError, XiaomiVacuumApiClientError
    )


def test_init_builds_sdk_client(mock_miot_device):
    with patch("custom_components.xiaomi_vacuum.api.client.MiotClient") as cls:
        XiaomiVacuumApiClient(host="1.2.3.4", token="t" * 32, spec=D109GL)
        cls.assert_called_once_with("1.2.3.4", "t" * 32, timeout=10.0)


async def test_async_get_info_returns_info(mock_miot_device):
    info = await _client(mock_miot_device).async_get_info()
    assert info.model == "xiaomi.vacuum.d109gl"


async def test_async_get_info_translates_miot_error(mock_miot_device):
    mock_miot_device.info.side_effect = MiotConnectionError("offline")
    with pytest.raises(XiaomiVacuumApiClientCommunicationError, match="Device error"):
        await _client(mock_miot_device).async_get_info()


async def test_async_get_info_unexpected_exception(mock_miot_device):
    mock_miot_device.info.side_effect = RuntimeError("boom")
    with pytest.raises(XiaomiVacuumApiClientError, match="Unexpected error"):
        await _client(mock_miot_device).async_get_info()


async def test_async_get_state_requests_spec_mapping(mock_miot_device):
    state = await _client(mock_miot_device).async_get_state()
    assert state["status"] == 2
    assert state["battery_level"] == 99
    assert state["sweep_mop_type"] == 1
    requested = mock_miot_device.get_properties.await_args.args[0]
    assert requested["status"] == PropertyAddress(
        siid=D109GL.property_mapping["status"]["siid"],
        piid=D109GL.property_mapping["status"]["piid"],
    )
    assert set(requested) == set(D109GL.property_mapping)


async def test_async_get_state_passes_through_missing_values(mock_miot_device):
    mock_miot_device.get_properties.side_effect = None
    mock_miot_device.get_properties.return_value = {"status": 4, "battery_level": None}
    state = await _client(mock_miot_device).async_get_state()
    assert state["status"] == 4
    assert state["battery_level"] is None


async def test_async_start_calls_action(mock_miot_device):
    await _client(mock_miot_device).async_start()
    mock_miot_device.call_action.assert_called_with(
        _action_address(D109GL.actions.start_sweep)
    )


async def test_async_pause_calls_action(mock_miot_device):
    await _client(mock_miot_device).async_pause()
    mock_miot_device.call_action.assert_called_with(
        _action_address(D109GL.actions.pause_sweeping)
    )


async def test_async_stop_calls_action(mock_miot_device):
    await _client(mock_miot_device).async_stop()
    mock_miot_device.call_action.assert_called_with(
        _action_address(D109GL.actions.stop_sweeping)
    )


async def test_async_return_home_calls_action(mock_miot_device):
    await _client(mock_miot_device).async_return_home()
    mock_miot_device.call_action.assert_called_with(
        _action_address(D109GL.actions.return_home)
    )


async def test_async_locate_calls_action(mock_miot_device):
    await _client(mock_miot_device).async_locate()
    mock_miot_device.call_action.assert_called_with(
        _action_address(D109GL.actions.identify)
    )


async def test_action_swallows_user_ack_timeout(mock_miot_device):
    """A -9999 ack timeout is treated as accepted; no exception to HA."""
    mock_miot_device.call_action.side_effect = MiotAckTimeoutError(
        "action", "user ack timeout"
    )
    # Should not raise — the optimistic UI + refresh reconciles the real state.
    await _client(mock_miot_device).async_start()


async def test_action_still_raises_non_ack_timeout_device_error(mock_miot_device):
    """A genuine device error (not ack-timeout) still surfaces as a comm error."""
    mock_miot_device.call_action.side_effect = MiotDeviceError(
        "action", -7, "real failure"
    )
    with pytest.raises(XiaomiVacuumApiClientCommunicationError):
        await _client(mock_miot_device).async_start()


async def test_async_set_fan_speed_unknown_raises(mock_miot_device):
    with pytest.raises(XiaomiVacuumApiClientError, match="Unknown fan speed"):
        await _client(mock_miot_device).async_set_fan_speed("turbocharge")


async def test_async_set_fan_speed_known_writes_property(mock_miot_device):
    await _client(mock_miot_device).async_set_fan_speed("strong")
    prop = D109GL.property_mapping["fan_speed"]
    mock_miot_device.set_property.assert_called_with(
        PropertyAddress(siid=prop["siid"], piid=prop["piid"]), 3
    )


async def test_async_set_sweep_mop_type_unknown_raises(mock_miot_device):
    with pytest.raises(XiaomiVacuumApiClientError, match="Unknown sweep_mop_type"):
        await _client(mock_miot_device).async_set_sweep_mop_type("invalid")


async def test_async_set_sweep_mop_type_writes_property(mock_miot_device):
    await _client(mock_miot_device).async_set_sweep_mop_type("mop")
    prop = D109GL.property_mapping["sweep_mop_type"]
    mock_miot_device.set_property.assert_called_with(
        PropertyAddress(siid=prop["siid"], piid=prop["piid"]), 2
    )


async def test_async_set_property_unknown_name_raises(mock_miot_device):
    with pytest.raises(XiaomiVacuumApiClientError, match="Unknown property"):
        await _client(mock_miot_device).async_set_property("does_not_exist", 1)


async def test_async_set_property_writes_value(mock_miot_device):
    await _client(mock_miot_device).async_set_property("clean_times", 2)
    prop = D109GL.property_mapping["clean_times"]
    mock_miot_device.set_property.assert_called_with(
        PropertyAddress(siid=prop["siid"], piid=prop["piid"]), 2
    )


async def test_async_clean_segments_payload(mock_miot_device):
    await _client(mock_miot_device).async_clean_segments(["10", "28"])
    args = mock_miot_device.call_action.call_args.args
    a = D109GL.actions.start_room_sweep
    assert args[0] == ActionAddress(siid=a["siid"], aiid=a["aiid"])
    assert args[1] == [{"piid": a["in_piid"], "value": "10,28"}]


async def test_async_clean_segments_coerces_int_ids(mock_miot_device):
    await _client(mock_miot_device).async_clean_segments([10, 28])
    args = mock_miot_device.call_action.call_args.args
    assert args[1][0]["value"] == "10,28"


_ROOM_INFO_TABLE = (
    '{"version":2,"room_attrs":[["id","room_name","fan_level","water_level",'
    '"clean_mode","clean_times","mop_mode","on"],'
    '[3,"Living room",4,3,1,1,0,false],'
    '[4,"Kitchen",4,3,3,1,0,false],'
    '[5,"Hall",4,3,3,1,0,true]]}'
)


async def test_b108_clean_segments_uses_two_step_flow(mock_miot_device_b108):
    """S20+ marks rooms via set-room-clean-configs then fires start-custom-sweep."""
    client = _client(mock_miot_device_b108, spec=B108GL)
    await client.async_clean_segments(["5"], room_information=_ROOM_INFO_TABLE)

    calls = mock_miot_device_b108.call_action.call_args_list
    # First: set-room-clean-configs (siid 2 / aiid 10) with the room_attrs JSON.
    set_call = calls[0].args
    assert set_call[0] == ActionAddress(siid=2, aiid=10)
    import json as _json

    payload = _json.loads(set_call[1][0])
    # Selected room (id 5) is emitted first; unselected keep their order.
    assert [r["id"] for r in payload["room_attrs"]] == [5, 3, 4]
    # Only the requested room (id 5) is flagged on=True.
    on_flags = {r["id"]: r["on"] for r in payload["room_attrs"]}
    assert on_flags == {3: False, 4: False, 5: True}

    # Second: start-custom-sweep (siid 6 / aiid 7) with empty input.
    start_call = calls[1].args
    assert start_call[0] == ActionAddress(siid=6, aiid=7)
    assert start_call[1] == []


async def test_b108_clean_segments_refuses_without_room_info(mock_miot_device_b108):
    """Without room_information the S20+ cannot build the config — refuse clearly."""
    client = _client(mock_miot_device_b108, spec=B108GL)
    with pytest.raises(XiaomiVacuumApiClientError, match="no room information"):
        await client.async_clean_segments(["5"], room_information=None)
    mock_miot_device_b108.call_action.assert_not_called()


def test_build_room_clean_config_marks_requested_rooms():
    rooms = _build_room_clean_config(_ROOM_INFO_TABLE, ["5"])
    assert {r["id"] for r in rooms} == {3, 4, 5}
    assert next(r for r in rooms if r["id"] == 5)["on"] is True
    assert all(r["on"] is False for r in rooms if r["id"] != 5)


def test_build_room_clean_config_preserves_requested_sequence():
    """Selected rooms come first, in the order the caller requested."""
    # Device order is [3,4,5]; request [5,3] (reversed for two of them).
    rooms = _build_room_clean_config(_ROOM_INFO_TABLE, ["5", "3"])
    selected = [r for r in rooms if r["on"]]
    others = [r for r in rooms if not r["on"]]
    # Selected rooms emitted in the requested order (5 then 3), before others.
    assert [r["id"] for r in selected] == [5, 3]
    assert [r["id"] for r in others] == [4]
    assert [r["id"] for r in rooms] == [5, 3, 4]


def test_build_room_clean_config_empty_when_no_room_info():
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
    rooms = _build_room_clean_config(_ROOM_INFO_TABLE_MIXED_CASE, ["5"])
    assert {r["id"] for r in rooms} == {3, 4, 5}
    assert next(r for r in rooms if r["id"] == 5)["on"] is True
    assert all(r["on"] is False for r in rooms if r["id"] != 5)


async def test_b108_clean_segments_routes_through_cloud_when_available(
    mock_miot_device_b108,
):
    """When a cloud session is attached, the S20+ room-clean uses the cloud path."""
    client = _client(mock_miot_device_b108, spec=B108GL)
    cloud = AsyncMock()
    # Successful cloud action responses carry code 0.
    cloud.async_call_action = AsyncMock(return_value={"code": 0, "message": "ok"})
    client.set_cloud(cloud)

    await client.async_clean_segments(["5"], room_information=_ROOM_INFO_TABLE)

    # Both actions go through the cloud (never touches the local device).
    mock_miot_device_b108.call_action.assert_not_called()
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


async def test_b108_clean_segments_cloud_reject_raises(mock_miot_device_b108):
    """A non-zero device code from the cloud surfaces as a clear error."""
    client = _client(mock_miot_device_b108, spec=B108GL)
    cloud = AsyncMock()
    cloud.async_call_action = AsyncMock(
        return_value={"code": -7, "message": "invalid params"}
    )
    client.set_cloud(cloud)
    with pytest.raises(XiaomiVacuumApiClientError, match="rejected by device"):
        await client.async_clean_segments(["5"], room_information=_ROOM_INFO_TABLE)


async def test_b108_clean_segments_cloud_none_falls_back_to_local(
    mock_miot_device_b108,
):
    """A ``None`` cloud response means no transport — fall back to the local path.

    Regression guard: a ``None`` result previously skipped the ``code`` check and
    silently succeeded while nothing actually ran on the device (the optimistic
    UI had already reported the clean as started).
    """
    client = _client(mock_miot_device_b108, spec=B108GL)
    cloud = AsyncMock()
    # ``async_call_action`` returns None when the cloud has no active session or
    # no resolved device — i.e. the transport is unavailable, not success.
    cloud.async_call_action = AsyncMock(return_value=None)
    client.set_cloud(cloud)

    await client.async_clean_segments(["5"], room_information=_ROOM_INFO_TABLE)

    # Both actions fall through to the local transport.
    assert cloud.async_call_action.await_count == 2
    assert mock_miot_device_b108.call_action.call_count == 2


async def test_b108_clean_segments_cloud_unreachable_falls_back_to_local(
    mock_miot_device_b108,
):
    """A cloud network failure falls back to local instead of failing the command."""
    from custom_components.xiaomi_vacuum.cloud import XiaomiCloudConnectionError

    client = _client(mock_miot_device_b108, spec=B108GL)
    cloud = AsyncMock()
    cloud.async_call_action = AsyncMock(
        side_effect=XiaomiCloudConnectionError("dns failure")
    )
    client.set_cloud(cloud)

    await client.async_clean_segments(["5"], room_information=_ROOM_INFO_TABLE)

    assert cloud.async_call_action.await_count == 2
    assert mock_miot_device_b108.call_action.call_count == 2


async def test_b108_clean_segments_expired_session_falls_back_to_local(
    mock_miot_device_b108,
):
    """A rejected session (expired token) must not fail the room clean."""
    from custom_components.xiaomi_vacuum.cloud import XiaomiCloudAuthError

    client = _client(mock_miot_device_b108, spec=B108GL)
    cloud = AsyncMock()
    cloud.async_call_action = AsyncMock(side_effect=XiaomiCloudAuthError("HTTP 401"))
    client.set_cloud(cloud)

    await client.async_clean_segments(["5"], room_information=_ROOM_INFO_TABLE)

    assert cloud.async_call_action.await_count == 2
    assert mock_miot_device_b108.call_action.call_count == 2


async def test_b108_return_home_uses_battery_service(mock_miot_device_b108):
    """S20+ return-home hits the battery.start-charge action, not SIID 2/aiid 3."""
    await _client(mock_miot_device_b108, spec=B108GL).async_return_home()
    a = B108GL.actions.return_home
    mock_miot_device_b108.call_action.assert_called_with(_action_address(a))
    assert a == {"siid": 3, "aiid": 1}


async def test_b108_continue_uses_vacuum_extend_service(mock_miot_device_b108):
    """S20+ continue-sweep lives on the vacuum-extend service (SIID 6 / aiid 1)."""
    await _client(mock_miot_device_b108, spec=B108GL).async_continue()
    a = B108GL.actions.continue_sweep
    assert a == {"siid": 6, "aiid": 1}
    mock_miot_device_b108.call_action.assert_called_with(_action_address(a))


async def test_b108_dust_arrest_raises(mock_miot_device_b108):
    """S20+ has no auto-dust dock; the action must surface a clear error."""
    with pytest.raises(XiaomiVacuumApiClientError, match="no dust-arrest"):
        await _client(mock_miot_device_b108, spec=B108GL).async_start_dust_arrest()


async def test_run_propagates_miot_error_as_communication_error(mock_miot_device):
    mock_miot_device.call_action.side_effect = MiotConnectionError("timeout")
    with pytest.raises(XiaomiVacuumApiClientCommunicationError):
        await _client(mock_miot_device).async_start()


async def test_run_propagates_unexpected_as_api_error(mock_miot_device):
    mock_miot_device.call_action.side_effect = ValueError("bad")
    with pytest.raises(XiaomiVacuumApiClientError, match="Unexpected"):
        await _client(mock_miot_device).async_start()
