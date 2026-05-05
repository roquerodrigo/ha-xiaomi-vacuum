from __future__ import annotations

from custom_components.xiaomi_vacuum.const import ACTION_START_DUST_ARREST


async def test_button_entity_exists(hass, setup_integration):
    state = hass.states.get("button.aspirador_collect_dust")
    assert state is not None


async def test_button_press_calls_dust_arrest(
    hass, setup_integration, mock_miot_device
):
    mock_miot_device.call_action_by.reset_mock()
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.aspirador_collect_dust"},
        blocking=True,
    )
    mock_miot_device.call_action_by.assert_called_with(
        ACTION_START_DUST_ARREST["siid"], ACTION_START_DUST_ARREST["aiid"]
    )


async def test_button_has_icon_and_no_category(hass, setup_integration):
    from homeassistant.helpers.entity_registry import async_get

    er = async_get(hass)
    entry = er.async_get("button.aspirador_collect_dust")
    assert entry is not None
    assert entry.entity_category is None

    state = hass.states.get("button.aspirador_collect_dust")
    assert state.attributes.get("icon") == "mdi:delete-empty"


async def test_api_client_async_start_dust_arrest(hass, mock_miot_device):
    from custom_components.xiaomi_vacuum.api import XiaomiVacuumApiClient

    client = XiaomiVacuumApiClient(hass=hass, host="1.2.3.4", token="t" * 32)
    await client.async_start_dust_arrest()
    mock_miot_device.call_action_by.assert_called_with(
        ACTION_START_DUST_ARREST["siid"], ACTION_START_DUST_ARREST["aiid"]
    )
