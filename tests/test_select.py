from __future__ import annotations

import pytest
from homeassistant.const import EntityCategory


async def test_setup_creates_5_select_entities(hass, setup_integration):
    states = hass.states.async_all("select")
    assert len(states) == 5


async def test_select_clean_times_current_option(hass, setup_integration):
    state = hass.states.get("select.vacuum_clean_times")
    assert state is not None
    # clean_times:1 -> "one_time"
    assert state.state == "one_time"


async def test_select_mop_water_level_current_option(hass, setup_integration):
    state = hass.states.get("select.vacuum_mop_water_level")
    # mop_water_level:1 -> "level_1"
    assert state.state == "level_1"


async def test_select_sweep_route(hass, setup_integration):
    state = hass.states.get("select.vacuum_sweep_route")
    # sweep_route:2 -> "daily"
    assert state.state == "daily"


async def test_select_obstacle_avoidance(hass, setup_integration):
    state = hass.states.get("select.vacuum_obstacle_avoidance")
    # 0 -> less_collisions
    assert state.state == "less_collisions"


async def test_select_options_listed(hass, setup_integration):
    state = hass.states.get("select.vacuum_clean_times")
    assert "one_time" in state.attributes["options"]
    assert "two_times" in state.attributes["options"]


async def test_select_entity_category_is_config(hass, setup_integration):
    from homeassistant.helpers.entity_registry import async_get

    er = async_get(hass)
    entry = er.async_get("select.vacuum_clean_times")
    assert entry is not None
    assert entry.entity_category == EntityCategory.CONFIG


async def test_select_option_calls_set_property(
    hass, setup_integration, mock_miot_device
):
    mock_miot_device.set_property.reset_mock()
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.vacuum_clean_times", "option": "two_times"},
        blocking=True,
    )
    assert mock_miot_device.set_property.called


async def test_select_option_optimistic_update(
    hass, setup_integration, mock_miot_device
):
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.vacuum_sweep_route", "option": "careful"},
        blocking=True,
    )
    state = hass.states.get("select.vacuum_sweep_route")
    assert state.state == "careful"


async def test_sweep_mop_type_sweep_allowed_without_mop_pad(
    hass, setup_integration, mock_miot_device
):
    """'sweep' mode does not need a mop pad — works even when detached."""
    coord = setup_integration.runtime_data.coordinator
    coord.async_set_updated_data({**coord.data, "mop_status": False})
    await hass.async_block_till_done()
    mock_miot_device.set_property.reset_mock()
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.vacuum_mode", "option": "sweep"},
        blocking=True,
    )
    assert mock_miot_device.set_property.called


async def test_sweep_mop_type_mop_rejected_without_mop_pad(
    hass, setup_integration, mock_miot_device
):
    """Mop modes must raise a clear error when the mop pad is not attached."""
    from homeassistant.exceptions import ServiceValidationError

    coord = setup_integration.runtime_data.coordinator
    coord.async_set_updated_data({**coord.data, "mop_status": False})
    await hass.async_block_till_done()
    mock_miot_device.set_property.reset_mock()
    with pytest.raises(ServiceValidationError, match="no mop pad detected"):
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": "select.vacuum_mode", "option": "sweep_mop"},
            blocking=True,
        )
    # The write must not have been sent to the device.
    mock_miot_device.set_property.assert_not_called()


@pytest.mark.parametrize("detached", [False, 0])
async def test_sweep_mop_type_mop_rejected_when_pad_reported_as_int(
    hass, setup_integration, mock_miot_device, detached
):
    """A device publishing the pad state as 0 must block mop modes just like False."""
    from homeassistant.exceptions import ServiceValidationError

    coord = setup_integration.runtime_data.coordinator
    coord.async_set_updated_data({**coord.data, "mop_status": detached})
    await hass.async_block_till_done()
    mock_miot_device.set_property.reset_mock()
    with pytest.raises(ServiceValidationError, match="no mop pad detected"):
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": "select.vacuum_mode", "option": "mop"},
            blocking=True,
        )
    mock_miot_device.set_property.assert_not_called()


async def test_sweep_mop_type_mop_allowed_when_pad_state_unknown(
    hass, setup_integration, mock_miot_device
):
    """An unreported pad state must not block the write — only a known-off one does."""
    coord = setup_integration.runtime_data.coordinator
    coord.async_set_updated_data({**coord.data, "mop_status": None})
    await hass.async_block_till_done()
    mock_miot_device.set_property.reset_mock()
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.vacuum_mode", "option": "sweep_mop"},
        blocking=True,
    )
    assert mock_miot_device.set_property.called


async def test_sweep_mop_type_mop_allowed_with_mop_pad(
    hass, setup_integration, mock_miot_device
):
    """Mop modes work fine when the mop pad is attached (default mock state)."""
    mock_miot_device.set_property.reset_mock()
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.vacuum_mode", "option": "sweep_mop"},
        blocking=True,
    )
    assert mock_miot_device.set_property.called


def test_every_select_has_an_authored_icon():
    """Each select translation key carries an icons.json default icon."""
    import json
    from pathlib import Path

    icons_path = (
        Path(__file__).parent.parent
        / "custom_components"
        / "xiaomi_vacuum"
        / "icons.json"
    )
    select_icons = json.loads(icons_path.read_text(encoding="utf-8"))["entity"][
        "select"
    ]
    assert select_icons["sweep_mop_type"]["default"] == "mdi:broom"
    expected_keys = {
        "sweep_mop_type",
        "clean_times",
        "mop_water_level",
        "sweep_route",
        "obstacle_avoidance_strategy",
    }
    assert set(select_icons) == expected_keys
    assert all(entry["default"].startswith("mdi:") for entry in select_icons.values())
