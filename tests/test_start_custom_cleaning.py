from __future__ import annotations

import json

from homeassistant.helpers.service import async_get_all_descriptions
from xiaomi_vacuum_sdk import MiotConnectionError

from custom_components.xiaomi_vacuum.const import DOMAIN
from custom_components.xiaomi_vacuum.vacuum.start_custom_cleaning import (
    async_refresh_custom_cleaning_options,
)

_CONFIG = json.dumps(
    {
        "user_labels": [
            {"id": 836314484, "name": "Afternoon cleaning"},
            {"id": 131206493, "name": "Litter box"},
        ]
    }
)


def _serve_custom_cleanings(mock_miot_device, config):
    poll = mock_miot_device.get_properties.side_effect

    def get_properties(mapping, **kwargs):
        if "config" in mapping:
            return {"config": config}
        return poll(mapping, **kwargs)

    mock_miot_device.get_properties.side_effect = get_properties


async def _name_selector(hass):
    descriptions = await async_get_all_descriptions(hass)
    return descriptions[DOMAIN]["start_custom_cleaning"]["fields"]["name"]["selector"]


async def test_setup_without_cleanings_offers_free_text(hass, setup_integration):
    assert await _name_selector(hass) == {
        "select": {"options": [], "custom_value": True}
    }


async def test_refresh_offers_the_vacuum_cleanings(
    hass, setup_integration, mock_miot_device
):
    _serve_custom_cleanings(mock_miot_device, _CONFIG)
    await async_refresh_custom_cleaning_options(hass, setup_integration)
    assert await _name_selector(hass) == {
        "select": {
            "options": ["Afternoon cleaning", "Litter box"],
            "custom_value": True,
        }
    }
    descriptions = await async_get_all_descriptions(hass)
    assert descriptions[DOMAIN]["start_custom_cleaning"]["target"] == {
        "entity": {"integration": DOMAIN, "domain": "vacuum"}
    }


async def test_refresh_skips_unreachable_vacuum(
    hass, setup_integration, mock_miot_device
):
    _serve_custom_cleanings(mock_miot_device, _CONFIG)
    setup_integration.runtime_data.coordinator.last_update_success = False
    await async_refresh_custom_cleaning_options(hass, setup_integration)
    assert setup_integration.runtime_data.custom_cleanings == ()


async def test_refresh_tolerates_read_failure(
    hass, setup_integration, mock_miot_device
):
    mock_miot_device.get_properties.side_effect = MiotConnectionError("timeout")
    await async_refresh_custom_cleaning_options(hass, setup_integration)
    assert setup_integration.runtime_data.custom_cleanings == ()


async def test_refresh_skips_model_without_custom_cleanings(
    hass, setup_integration_b108, mock_miot_device_b108
):
    mock_miot_device_b108.get_properties.reset_mock()
    await async_refresh_custom_cleaning_options(hass, setup_integration_b108)
    mock_miot_device_b108.get_properties.assert_not_called()


async def test_action_call_updates_the_options(
    hass, setup_integration, mock_miot_device
):
    _serve_custom_cleanings(mock_miot_device, _CONFIG)
    await hass.services.async_call(
        DOMAIN,
        "start_custom_cleaning",
        {"entity_id": "vacuum.vacuum", "name": "Litter box"},
        blocking=True,
    )
    assert (await _name_selector(hass))["select"]["options"] == [
        "Afternoon cleaning",
        "Litter box",
    ]
