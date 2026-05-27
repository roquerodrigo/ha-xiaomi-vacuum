from __future__ import annotations

from unittest.mock import patch

import pytest
from miio import DeviceException

from custom_components.xiaomi_vacuum.api import (
    XiaomiVacuumApiClient,
    XiaomiVacuumApiClientCommunicationError,
    XiaomiVacuumApiClientError,
)
from custom_components.xiaomi_vacuum.const import (
    ACTION_IDENTIFY,
    ACTION_PAUSE_SWEEPING,
    ACTION_RETURN_HOME,
    ACTION_START_ROOM_SWEEP,
    ACTION_START_SWEEP,
    ACTION_STOP_SWEEPING,
    PROPERTY_MAPPING,
)


def _client(hass, mock_miot_device):
    return XiaomiVacuumApiClient(hass=hass, host="1.2.3.4", token="t" * 32)


def test_communication_error_is_api_error():
    assert issubclass(
        XiaomiVacuumApiClientCommunicationError, XiaomiVacuumApiClientError
    )


def test_init_passes_mapping_to_miot_device(hass, mock_miot_device):
    with patch("custom_components.xiaomi_vacuum.api.client.MiotDevice") as cls:
        XiaomiVacuumApiClient(hass=hass, host="1.2.3.4", token="t" * 32)
        cls.assert_called_once_with(
            ip="1.2.3.4", token="t" * 32, mapping=PROPERTY_MAPPING
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
    mock_miot_device.call_action_by.assert_called_with(
        ACTION_START_SWEEP["siid"], ACTION_START_SWEEP["aiid"]
    )


async def test_async_pause_calls_action(hass, mock_miot_device):
    await _client(hass, mock_miot_device).async_pause()
    mock_miot_device.call_action_by.assert_called_with(
        ACTION_PAUSE_SWEEPING["siid"], ACTION_PAUSE_SWEEPING["aiid"]
    )


async def test_async_stop_calls_action(hass, mock_miot_device):
    await _client(hass, mock_miot_device).async_stop()
    mock_miot_device.call_action_by.assert_called_with(
        ACTION_STOP_SWEEPING["siid"], ACTION_STOP_SWEEPING["aiid"]
    )


async def test_async_return_home_calls_action(hass, mock_miot_device):
    await _client(hass, mock_miot_device).async_return_home()
    mock_miot_device.call_action_by.assert_called_with(
        ACTION_RETURN_HOME["siid"], ACTION_RETURN_HOME["aiid"]
    )


async def test_async_locate_calls_action(hass, mock_miot_device):
    await _client(hass, mock_miot_device).async_locate()
    mock_miot_device.call_action_by.assert_called_with(
        ACTION_IDENTIFY["siid"], ACTION_IDENTIFY["aiid"]
    )


async def test_async_set_fan_speed_unknown_raises(hass, mock_miot_device):
    with pytest.raises(XiaomiVacuumApiClientError, match="Unknown fan speed"):
        await _client(hass, mock_miot_device).async_set_fan_speed("turbocharge")


async def test_async_set_fan_speed_known_writes_property(hass, mock_miot_device):
    await _client(hass, mock_miot_device).async_set_fan_speed("strong")
    prop = PROPERTY_MAPPING["fan_speed"]
    mock_miot_device.set_property_by.assert_called_with(prop["siid"], prop["piid"], 3)


async def test_async_set_sweep_mop_type_unknown_raises(hass, mock_miot_device):
    with pytest.raises(XiaomiVacuumApiClientError, match="Unknown sweep_mop_type"):
        await _client(hass, mock_miot_device).async_set_sweep_mop_type("invalid")


async def test_async_set_sweep_mop_type_writes_property(hass, mock_miot_device):
    await _client(hass, mock_miot_device).async_set_sweep_mop_type("mop")
    prop = PROPERTY_MAPPING["sweep_mop_type"]
    mock_miot_device.set_property_by.assert_called_with(prop["siid"], prop["piid"], 2)


async def test_async_set_property_unknown_name_raises(hass, mock_miot_device):
    with pytest.raises(XiaomiVacuumApiClientError, match="Unknown property"):
        await _client(hass, mock_miot_device).async_set_property("does_not_exist", 1)


async def test_async_set_property_writes_value(hass, mock_miot_device):
    await _client(hass, mock_miot_device).async_set_property("clean_times", 2)
    prop = PROPERTY_MAPPING["clean_times"]
    mock_miot_device.set_property_by.assert_called_with(prop["siid"], prop["piid"], 2)


async def test_async_clean_segments_payload(hass, mock_miot_device):
    await _client(hass, mock_miot_device).async_clean_segments(["10", "28"])
    args = mock_miot_device.call_action_by.call_args.args
    assert args[0] == ACTION_START_ROOM_SWEEP["siid"]
    assert args[1] == ACTION_START_ROOM_SWEEP["aiid"]
    assert args[2] == [{"piid": ACTION_START_ROOM_SWEEP["in_piid"], "value": "10,28"}]


async def test_async_clean_segments_coerces_int_ids(hass, mock_miot_device):
    await _client(hass, mock_miot_device).async_clean_segments([10, 28])
    args = mock_miot_device.call_action_by.call_args.args
    assert args[2][0]["value"] == "10,28"


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
