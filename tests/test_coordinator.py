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
)


def _coord_with_client(hass, client_mock):
    coord = XiaomiVacuumDataUpdateCoordinator(hass=hass)
    runtime = type("R", (), {"client": client_mock})()
    coord.config_entry = type("E", (), {"runtime_data": runtime})()
    return coord


def test_update_interval_is_30s():
    assert timedelta(seconds=30) == UPDATE_INTERVAL


def test_init_sets_domain_name(hass):
    assert XiaomiVacuumDataUpdateCoordinator(hass=hass).name == DOMAIN


async def test_async_update_data_returns_state(hass, sample_state):
    client = type("C", (), {"async_get_state": AsyncMock(return_value=sample_state)})()
    coord = _coord_with_client(hass, client)
    result = await coord._async_update_data()
    assert result == sample_state


async def test_async_update_data_raises_update_failed_on_api_error(hass):
    client = type(
        "C",
        (),
        {"async_get_state": AsyncMock(side_effect=XiaomiVacuumApiClientError("oops"))},
    )()
    coord = _coord_with_client(hass, client)
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()
