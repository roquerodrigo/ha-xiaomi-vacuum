from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

pytest_plugins = "pytest_homeassistant_custom_component"

SAMPLE_ROOM_INFO = json.dumps(
    {
        "rooms": [
            {"id": 10, "name": "Escritório"},
            {"id": 28, "name": "Sala"},
        ],
        "map_uid": 5,
    }
)

SAMPLE_STATE: dict[str, Any] = {
    "status": 2,
    "fault": 0,
    "sweep_mop_type": 1,
    "cleaning_area": 200,
    "cleaning_time": 120,
    "clean_times": 1,
    "fan_speed": 2,
    "mop_water_level": 1,
    "room_information": SAMPLE_ROOM_INFO,
    "last_clean_time": 1700000000,
    "sweep_route": 2,
    "obstacle_avoidance_strategy": 0,
    "battery_level": 99,
    "charging_state": 1,
}


@pytest.fixture
def sample_state() -> dict[str, Any]:
    return dict(SAMPLE_STATE)


@pytest.fixture
def sample_room_info() -> str:
    return SAMPLE_ROOM_INFO


@pytest.fixture
def enable_custom_integrations(hass) -> None:
    from homeassistant.loader import DATA_CUSTOM_COMPONENTS

    hass.data.pop(DATA_CUSTOM_COMPONENTS, None)


@pytest.fixture
def mock_miot_device() -> Generator:
    """Patch miio.MiotDevice everywhere it's imported."""
    with patch("custom_components.xiaomi_vacuum.api.MiotDevice") as cls:
        instance = cls.return_value
        info = MagicMock()
        info.model = "xiaomi.vacuum.d109gl"
        info.mac_address = "AA:BB:CC:DD:EE:FF"
        info.firmware_version = "1.0.0"
        info.hardware_version = "rev1"
        info.raw = {"model": "xiaomi.vacuum.d109gl", "mac": "AA:BB:CC:DD:EE:FF"}
        instance.info = MagicMock(return_value=info)
        instance.set_property_by = MagicMock(return_value=None)
        instance.call_action_by = MagicMock(return_value=None)
        instance.get_properties_for_mapping = MagicMock(
            return_value=_state_to_rows(SAMPLE_STATE)
        )
        yield instance


def _state_to_rows(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Build raw MIoT rows from a parsed state dict (mimics device echoing did)."""
    from custom_components.xiaomi_vacuum.const import PROPERTY_MAPPING

    rows = []
    for name, value in state.items():
        prop = PROPERTY_MAPPING.get(name)
        if prop is None:
            continue
        rows.append(
            {
                "did": "1234567890",
                "siid": prop["siid"],
                "piid": prop["piid"],
                "code": 0,
                "value": value,
            }
        )
    return rows


@pytest.fixture
async def setup_integration(hass, mock_miot_device, enable_custom_integrations):
    """Set up the integration with mocked MIoT and return the entry."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.xiaomi_vacuum.const import (
        CONF_HOST,
        CONF_NAME,
        CONF_TOKEN,
        DOMAIN,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.1.50",
            CONF_TOKEN: "0" * 32,
            CONF_NAME: "Aspirador",
        },
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.fixture
def mock_api_client() -> Generator:
    """Mock XiaomiVacuumApiClient (for tests that bypass setup_integration)."""
    with patch("custom_components.xiaomi_vacuum.XiaomiVacuumApiClient") as cls:
        instance = cls.return_value
        info = MagicMock()
        info.model = "xiaomi.vacuum.d109gl"
        info.mac_address = "AA:BB:CC:DD:EE:FF"
        info.firmware_version = "1.0.0"
        info.hardware_version = "rev1"
        instance.async_get_info = AsyncMock(return_value=info)
        instance.async_get_state = AsyncMock(return_value=dict(SAMPLE_STATE))
        instance.async_start = AsyncMock()
        instance.async_pause = AsyncMock()
        instance.async_stop = AsyncMock()
        instance.async_return_home = AsyncMock()
        instance.async_locate = AsyncMock()
        instance.async_set_fan_speed = AsyncMock()
        instance.async_set_sweep_mop_type = AsyncMock()
        instance.async_set_property = AsyncMock()
        instance.async_clean_segments = AsyncMock()
        yield instance
