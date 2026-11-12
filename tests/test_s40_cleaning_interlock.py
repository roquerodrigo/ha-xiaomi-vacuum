"""Regression coverage for S40 Pro new-cleaning interlocks.

Only codes observed on physical S40 Pro hardware are included.
"""

from __future__ import annotations

import json

import pytest
from homeassistant.exceptions import ServiceValidationError

from custom_components.xiaomi_vacuum.spec import OV71GL
from custom_components.xiaomi_vacuum.vacuum import XiaomiVacuum


@pytest.mark.parametrize("code", [210013, 210020])
def test_known_missing_container_blocks_anywhere_in_fault_list(code):
    state = {"fault_ids": json.dumps({"ts": 123, "fault": [100027, 0, code]})}
    assert OV71GL.active_cleaning_blockers(state) == frozenset({code})


@pytest.mark.parametrize(
    "raw",
    [None, "", "garbage", '{"fault":null}', '{"fault":123}', '{"fault":[100027,0]}'],
)
def test_missing_malformed_or_phantom_payload_does_not_invent_blockers(raw):
    assert OV71GL.active_cleaning_blockers({"fault_ids": raw}) == frozenset()


def test_simultaneous_missing_containers_are_both_visible():
    state = {"fault_ids": '{"fault":[210013,210020,100027]}'}
    assert OV71GL.active_cleaning_blockers(state) == frozenset({210013, 210020})


@pytest.mark.parametrize("code", [210013, 210020])
async def test_new_s40_clean_is_rejected_before_device_call(
    hass, setup_integration_ov71, mock_miot_device_ov71, code
):
    coordinator = setup_integration_ov71.runtime_data.coordinator
    coordinator.async_set_updated_data(
        {
            **coordinator.data,
            "status": 9,
            "fault_ids": json.dumps({"fault": [100027, code]}),
        }
    )
    await hass.async_block_till_done()
    entity = XiaomiVacuum(coordinator=coordinator)
    entity.hass = hass
    mock_miot_device_ov71.call_action.reset_mock()

    with pytest.raises(ServiceValidationError, match=str(code)):
        await entity.async_start()

    with pytest.raises(ServiceValidationError, match=str(code)):
        await entity.async_clean_segments(["1"])

    with pytest.raises(ServiceValidationError, match=str(code)):
        await entity.async_clean_zone([[0, 0, 100, 100]])

    with pytest.raises(ServiceValidationError, match=str(code)):
        await entity.async_send_command("start_mop")

    mock_miot_device_ov71.call_action.assert_not_called()


async def test_return_home_and_resume_are_not_blocked(
    hass, setup_integration_ov71, mock_miot_device_ov71
):
    coordinator = setup_integration_ov71.runtime_data.coordinator
    coordinator.async_set_updated_data(
        {
            **coordinator.data,
            "fault_ids": '{"fault":[210013]}',
        }
    )
    await hass.async_block_till_done()
    entity = XiaomiVacuum(coordinator=coordinator)
    entity.hass = hass
    await entity.async_return_to_base()
    await entity.async_send_command("continue_sweep")
    assert mock_miot_device_ov71.call_action.call_count >= 2


@pytest.mark.parametrize("nonblocking_code", [100025, 210005])
async def test_nonblocking_fault_does_not_block_new_clean(
    hass, setup_integration_ov71, mock_miot_device_ov71, nonblocking_code
):
    coordinator = setup_integration_ov71.runtime_data.coordinator
    coordinator.async_set_updated_data(
        {
            **coordinator.data,
            "status": 9,
            "fault_ids": json.dumps({"fault": [100027, nonblocking_code]}),
            "fault": 0,
        }
    )
    await hass.async_block_till_done()
    entity = XiaomiVacuum(coordinator=coordinator)
    entity.hass = hass
    await entity.async_start()
    assert mock_miot_device_ov71.call_action.called
