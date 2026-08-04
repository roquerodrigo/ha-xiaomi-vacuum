from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.xiaomi_vacuum.api import (
    XiaomiVacuumApiClientCommunicationError,
    XiaomiVacuumApiClientError,
)
from custom_components.xiaomi_vacuum.const import CONF_HOST, DOMAIN
from custom_components.xiaomi_vacuum.coordinator import (
    UPDATE_INTERVAL,
    XiaomiVacuumDataUpdateCoordinator,
    _live_fault_code_ids,
)
from custom_components.xiaomi_vacuum.repairs import async_raise_cannot_connect
from custom_components.xiaomi_vacuum.spec import B108GL, D109GL


def _fake_entry(client_mock=None, spec=D109GL):
    runtime = type("R", (), {"client": client_mock, "spec": spec})()
    # `async_on_unload` is invoked by DataUpdateCoordinator.__init__ when a
    # config_entry is passed; a no-op is enough for these unit tests.
    # entry_id/title/data feed the cannot_connect repair issue helpers.
    return type(
        "E",
        (),
        {
            "runtime_data": runtime,
            "async_on_unload": lambda *_: None,
            "entry_id": "test-entry",
            "title": "Aspirador",
            "data": {CONF_HOST: "192.168.1.50"},
        },
    )()


def _coord_with_client(hass, client_mock, spec=D109GL):
    entry = _fake_entry(client_mock, spec=spec)
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


def test_live_fault_code_ids_zero_when_no_active_fault():
    assert _live_fault_code_ids('{"ts": 1, "fault": [0]}') == 0


def test_live_fault_code_ids_returns_active_code():
    assert _live_fault_code_ids('{"ts": 1, "fault": [210009]}') == 210009


def test_live_fault_code_ids_none_without_fault_ids():
    assert _live_fault_code_ids(None) is None


def test_live_fault_code_ids_none_on_bad_json():
    assert _live_fault_code_ids("not json") is None


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


async def test_update_failure_creates_repair_issue(hass):
    client = type(
        "C",
        (),
        {
            "async_get_state": AsyncMock(
                side_effect=XiaomiVacuumApiClientCommunicationError("off")
            )
        },
    )()
    coord = _coord_with_client(hass, client)
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()
    registry = ir.async_get(hass)
    assert registry.async_get_issue(DOMAIN, "cannot_connect_test-entry") is not None


async def test_non_communication_error_does_not_create_repair_issue(hass):
    client = type(
        "C",
        (),
        {"async_get_state": AsyncMock(side_effect=XiaomiVacuumApiClientError("bug"))},
    )()
    coord = _coord_with_client(hass, client)
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()
    registry = ir.async_get(hass)
    assert registry.async_get_issue(DOMAIN, "cannot_connect_test-entry") is None


async def test_update_success_clears_repair_issue(hass, sample_state):
    client = type("C", (), {"async_get_state": AsyncMock(return_value=sample_state)})()
    coord = _coord_with_client(hass, client)
    async_raise_cannot_connect(hass, coord.config_entry)
    await coord._async_update_data()
    registry = ir.async_get(hass)
    assert registry.async_get_issue(DOMAIN, "cannot_connect_test-entry") is None


def test_live_fault_code_ids_none_on_non_dict_json():
    # A JSON array has no `.get`, exercising the AttributeError branch.
    assert _live_fault_code_ids("[1, 2, 3]") is None


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


async def test_enrich_fault_text_starts_reauth_when_session_rejected(hass):
    from unittest.mock import MagicMock

    from custom_components.xiaomi_vacuum.cloud import XiaomiCloudAuthError

    state = {"fault_ids": '{"ts": 1, "fault": [210009]}'}
    client = type("C", (), {"async_get_state": AsyncMock(return_value=state)})()
    coord = _coord_with_client(hass, client)
    coord.config_entry.async_start_reauth = MagicMock()
    coord.cloud = type(
        "Cloud",
        (),
        {"async_fault_text": AsyncMock(side_effect=XiaomiCloudAuthError("401"))},
    )()
    result = await coord._async_update_data()
    assert result["fault"] == 210009
    assert "fault_text" not in result
    coord.config_entry.async_start_reauth.assert_called_once_with(hass)


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


async def test_b108_derives_fault_from_simple_uint32(hass):
    """S20+ (fault_kind=simple) reads the plain fault property as an int."""
    state = {"fault": 0}
    client = type("C", (), {"async_get_state": AsyncMock(return_value=state)})()
    coord = _coord_with_client(hass, client, spec=B108GL)
    result = await coord._async_update_data()
    assert result["fault"] == 0


async def test_b108_simple_fault_reports_nonzero_code(hass):
    state = {"fault": 210009}
    client = type("C", (), {"async_get_state": AsyncMock(return_value=state)})()
    coord = _coord_with_client(hass, client, spec=B108GL)
    result = await coord._async_update_data()
    assert result["fault"] == 210009
