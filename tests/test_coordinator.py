from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.xiaomi_vacuum.api import XiaomiVacuumApiClientError
from custom_components.xiaomi_vacuum.const import DOMAIN
from custom_components.xiaomi_vacuum.coordinator import (
    UPDATE_INTERVAL,
    XiaomiVacuumDataUpdateCoordinator,
    _live_fault_code,
)


def _fake_entry(client_mock=None):
    runtime = type("R", (), {"client": client_mock})()
    # `async_on_unload` is invoked by DataUpdateCoordinator.__init__ when a
    # config_entry is passed; a no-op is enough for these unit tests.
    return type(
        "E",
        (),
        {"runtime_data": runtime, "async_on_unload": lambda *_: None},
    )()


def _coord_with_client(hass, client_mock):
    entry = _fake_entry(client_mock)
    return XiaomiVacuumDataUpdateCoordinator(hass=hass, config_entry=entry)


def test_update_interval_is_30s():
    assert timedelta(seconds=30) == UPDATE_INTERVAL


def test_init_sets_domain_name(hass):
    coord = XiaomiVacuumDataUpdateCoordinator(hass=hass, config_entry=_fake_entry())
    assert coord.name == DOMAIN


async def test_async_update_data_returns_state(hass, sample_state):
    client = type("C", (), {"async_get_state": AsyncMock(return_value=sample_state)})()
    coord = _coord_with_client(hass, client)
    result = await coord._async_update_data()
    assert result == sample_state


def test_live_fault_code_zero_when_no_active_fault():
    assert _live_fault_code('{"ts": 1, "fault": [0]}') == 0


def test_live_fault_code_returns_active_code():
    assert _live_fault_code('{"ts": 1, "fault": [210009]}') == 210009


def test_live_fault_code_none_without_fault_ids():
    assert _live_fault_code(None) is None


def test_live_fault_code_none_on_bad_json():
    assert _live_fault_code("not json") is None


async def test_async_update_data_derives_fault_from_fault_ids(hass):
    state = {"fault_ids": '{"ts": 1, "fault": [0]}'}
    client = type("C", (), {"async_get_state": AsyncMock(return_value=state)})()
    coord = _coord_with_client(hass, client)
    result = await coord._async_update_data()
    assert result["fault"] == 0


async def test_async_update_data_raises_update_failed_on_api_error(hass):
    client = type(
        "C",
        (),
        {"async_get_state": AsyncMock(side_effect=XiaomiVacuumApiClientError("oops"))},
    )()
    coord = _coord_with_client(hass, client)
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()


def test_live_fault_code_none_on_non_dict_json():
    # A JSON array has no `.get`, exercising the AttributeError branch.
    assert _live_fault_code("[1, 2, 3]") is None


async def test_enrich_fault_text_adds_localized_text(hass):
    state = {"fault_ids": '{"ts": 1, "fault": [210009]}'}
    client = type("C", (), {"async_get_state": AsyncMock(return_value=state)})()
    coord = _coord_with_client(hass, client)
    cloud = type(
        "Cloud",
        (),
        {"async_fault_text": AsyncMock(return_value="Cannot return to dock")},
    )()
    coord.cloud = cloud
    result = await coord._async_update_data()
    assert result["fault"] == 210009
    assert result["fault_text"] == "Cannot return to dock"


async def test_enrich_fault_text_noop_without_cloud(hass):
    state = {"fault_ids": '{"ts": 1, "fault": [210009]}'}
    client = type("C", (), {"async_get_state": AsyncMock(return_value=state)})()
    coord = _coord_with_client(hass, client)
    coord.cloud = None
    result = await coord._async_update_data()
    assert "fault_text" not in result


async def test_enrich_fault_text_noop_when_code_zero(hass):
    state = {"fault_ids": '{"ts": 1, "fault": [0]}'}
    client = type("C", (), {"async_get_state": AsyncMock(return_value=state)})()
    coord = _coord_with_client(hass, client)
    fault_text = AsyncMock(return_value="should not be called")
    coord.cloud = type("Cloud", (), {"async_fault_text": fault_text})()
    result = await coord._async_update_data()
    assert "fault_text" not in result
    fault_text.assert_not_awaited()


async def test_enrich_fault_text_noop_when_text_missing(hass):
    state = {"fault_ids": '{"ts": 1, "fault": [210009]}'}
    client = type("C", (), {"async_get_state": AsyncMock(return_value=state)})()
    coord = _coord_with_client(hass, client)
    coord.cloud = type(
        "Cloud", (), {"async_fault_text": AsyncMock(return_value=None)}
    )()
    result = await coord._async_update_data()
    assert "fault_text" not in result
