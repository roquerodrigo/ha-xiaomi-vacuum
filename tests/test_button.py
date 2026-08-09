from __future__ import annotations

from xiaomi_vacuum_sdk import ActionAddress

from custom_components.xiaomi_vacuum.spec import D109GL


async def test_button_entity_exists(hass, setup_integration):
    state = hass.states.get("button.vacuum_collect_dust")
    assert state is not None


async def test_button_press_calls_dust_arrest(
    hass, setup_integration, mock_miot_device
):
    mock_miot_device.call_action.reset_mock()
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.vacuum_collect_dust"},
        blocking=True,
    )
    a = D109GL.actions.start_dust_arrest
    mock_miot_device.call_action.assert_called_with(
        ActionAddress(siid=a["siid"], aiid=a["aiid"])
    )


def test_button_has_icon_and_no_category(hass, setup_integration):
    import json
    from pathlib import Path

    from homeassistant.helpers.entity_registry import async_get

    er = async_get(hass)
    entry = er.async_get("button.vacuum_collect_dust")
    assert entry is not None
    assert entry.entity_category is None

    icons_path = (
        Path(__file__).parent.parent
        / "custom_components"
        / "xiaomi_vacuum"
        / "icons.json"
    )
    button_icons = json.loads(icons_path.read_text(encoding="utf-8"))["entity"][
        "button"
    ]
    assert button_icons["dust_arrest"]["default"] == "mdi:delete-empty"


async def test_api_client_async_start_dust_arrest(hass, mock_miot_device):
    from custom_components.xiaomi_vacuum.api import XiaomiVacuumApiClient

    client = XiaomiVacuumApiClient(host="1.2.3.4", token="t" * 32, spec=D109GL)
    await client.async_start_dust_arrest()
    a = D109GL.actions.start_dust_arrest
    mock_miot_device.call_action.assert_called_with(
        ActionAddress(siid=a["siid"], aiid=a["aiid"])
    )
