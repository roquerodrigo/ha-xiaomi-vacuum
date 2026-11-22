from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er

from custom_components.xiaomi_vacuum.cloud import (
    XiaomiCloudAuthError,
    XiaomiCloudConnectionError,
)
from custom_components.xiaomi_vacuum.const import DOMAIN
from custom_components.xiaomi_vacuum.spec import get_spec

from .conftest import MODEL_FIXTURES

_X20_MAX_FAULT_EVENT = {"siid": 2, "eiid": 3}
_FAULT_EVENT_BY_MODEL = {
    "xiaomi.vacuum.d109gl": _X20_MAX_FAULT_EVENT,
    "xiaomi.vacuum.ov71gl": _X20_MAX_FAULT_EVENT,
}


def _vacuum_entity_id(hass) -> str:
    (entity_id,) = hass.states.async_entity_ids("vacuum")
    return entity_id


def _error_code_entity_id(hass, entry) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_error_code"
    )
    assert entity_id is not None
    return entity_id


async def _refresh_fault_history(hass):
    return await hass.services.async_call(
        DOMAIN,
        "refresh_fault_history",
        {"entity_id": _vacuum_entity_id(hass)},
        blocking=True,
        return_response=True,
    )


def test_every_model_declares_only_an_observed_fault_event(model):
    assert get_spec(model).fault_event == _FAULT_EVENT_BY_MODEL.get(model)


async def test_fault_history_returns_the_cloud_events(
    hass, setup_integration_with_cloud, mock_cloud
):
    events = [{"code": 210013, "text": "Dust bin missing", "timestamp": 1794844808}]
    mock_cloud.async_fault_history = AsyncMock(return_value=events)

    response = await _refresh_fault_history(hass)

    assert response == {_vacuum_entity_id(hass): {"fault_history": events}}
    mock_cloud.async_fault_history.assert_awaited_once_with(_X20_MAX_FAULT_EVENT)


async def test_fault_history_requires_a_cloud_session(hass, setup_integration):
    with pytest.raises(ServiceValidationError) as raised:
        await _refresh_fault_history(hass)
    assert raised.value.translation_key == "fault_history_cloud_unavailable"


async def test_fault_history_starts_a_reauth_when_the_session_expired(
    hass, setup_integration_with_cloud, mock_cloud
):
    mock_cloud.async_fault_history = AsyncMock(side_effect=XiaomiCloudAuthError("x"))

    with pytest.raises(ServiceValidationError) as raised:
        await _refresh_fault_history(hass)

    assert raised.value.translation_key == "fault_history_session_expired"
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [flow["context"]["source"] for flow in flows] == ["reauth"]


async def test_fault_history_reports_a_failed_cloud_read(
    hass, setup_integration_with_cloud, mock_cloud
):
    mock_cloud.async_fault_history = AsyncMock(
        side_effect=XiaomiCloudConnectionError("x")
    )
    with pytest.raises(ServiceValidationError) as raised:
        await _refresh_fault_history(hass)
    assert raised.value.translation_key == "fault_history_read_failed"


@pytest.mark.parametrize(
    "unsupported_model",
    sorted(set(MODEL_FIXTURES) - set(_FAULT_EVENT_BY_MODEL)),
)
async def test_fault_history_is_refused_on_models_without_a_fault_event(
    hass, setup_model, unsupported_model
):
    await setup_model(unsupported_model)
    with pytest.raises(ServiceValidationError) as raised:
        await _refresh_fault_history(hass)
    assert raised.value.translation_key == "fault_history_unsupported"
    assert raised.value.translation_placeholders == {
        "model": get_spec(unsupported_model).name
    }


async def test_error_code_attributes_split_ignored_and_active_codes(hass, setup_model):
    entry, device = await setup_model("xiaomi.vacuum.ov71gl")
    state = dict(MODEL_FIXTURES["xiaomi.vacuum.ov71gl"]["state"])
    state["fault_ids"] = json.dumps({"ts": 1, "fault": [100027, 210020]})
    device.get_properties = AsyncMock(
        side_effect=lambda mapping, **_: {name: state.get(name) for name in mapping}
    )

    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    sensor = hass.states.get(_error_code_entity_id(hass, entry))
    assert sensor.state == "210020"
    assert sensor.attributes["raw_fault_codes"] == [100027, 210020]
    assert sensor.attributes["active_fault_codes"] == [210020]
    assert sensor.attributes["ignored_fault_codes"] == [100027]


async def test_error_code_attributes_keep_a_plain_phantom_code_as_raw(
    hass, setup_model
):
    entry, device = await setup_model("xiaomi.vacuum.c102gl")
    spec = get_spec("xiaomi.vacuum.c102gl")
    code = next(iter(spec.notice_fault_codes))
    state = dict(MODEL_FIXTURES["xiaomi.vacuum.c102gl"]["state"])
    state["fault"] = code
    device.get_properties = AsyncMock(
        side_effect=lambda mapping, **_: {name: state.get(name) for name in mapping}
    )

    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    sensor = hass.states.get(_error_code_entity_id(hass, entry))
    assert sensor.state == str(code)
    assert sensor.attributes["raw_fault_codes"] == [code]
    assert sensor.attributes["active_fault_codes"] == [code]
    assert sensor.attributes["ignored_fault_codes"] == []


@pytest.mark.parametrize("model_name", sorted(MODEL_FIXTURES))
def test_raw_fault_codes_report_unknown_payloads_as_none(model_name):
    assert get_spec(model_name).raw_fault_codes({}) is None


def test_primary_fault_code_prefers_a_real_fault_over_a_notice():
    spec = get_spec("xiaomi.vacuum.ov71gl")
    assert spec.primary_fault_code([210020, 100027, 210009]) == 210009
    assert spec.primary_fault_code([100027]) == 0
    assert spec.primary_fault_code(None) is None
    assert spec.active_fault_codes(None) is None
    assert spec.reported_ignored_fault_codes(None) is None
