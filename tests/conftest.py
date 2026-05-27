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
    with patch("custom_components.xiaomi_vacuum.api.client.MiotDevice") as cls:
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
def mock_cloud() -> Generator:
    """Mock XiaomiCloud (covers both `from_session` and `__init__` paths)."""
    with patch("custom_components.xiaomi_vacuum.XiaomiCloud") as cls:
        instance = cls.return_value
        cls.from_session = MagicMock(return_value=instance)
        device = MagicMock(country="cn", model="xiaomi.vacuum.d109gl", device_id="d")
        instance._device = device
        instance.async_resolve_device = AsyncMock(return_value=device)
        instance.async_get_map_bytes = AsyncMock(return_value=b"PNG_BYTES")
        yield instance


@pytest.fixture
async def setup_integration_with_cloud(
    hass, mock_miot_device, mock_cloud, enable_custom_integrations
):
    """Set up the integration with cloud session tokens populated."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.xiaomi_vacuum.const import (
        CONF_CLOUD_COUNTRY,
        CONF_CLOUD_SERVICE_TOKEN,
        CONF_CLOUD_SSECURITY,
        CONF_CLOUD_USER_ID,
        CONF_HOST,
        CONF_NAME,
        CONF_TOKEN,
        DOMAIN,
    )

    with patch(
        "custom_components.xiaomi_vacuum.map_coordinator.XiaomiMapDataParser"
    ) as parser_cls:
        parser = parser_cls.return_value
        map_data = MagicMock()
        image_obj = MagicMock()
        image_obj.data.save = MagicMock()
        map_data.image = image_obj
        parser.parse = MagicMock(return_value=map_data)
        parser.unpack_map = MagicMock(return_value="{}")

        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "192.168.1.50",
                CONF_TOKEN: "0" * 32,
                CONF_NAME: "Aspirador",
                CONF_CLOUD_COUNTRY: "cn",
                CONF_CLOUD_SSECURITY: "ssecurity_value",
                CONF_CLOUD_SERVICE_TOKEN: "service_token_value",
                CONF_CLOUD_USER_ID: "user_id_value",
            },
            unique_id="AA:BB:CC:DD:EE:FF",
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        yield entry
