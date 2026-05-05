from __future__ import annotations

from homeassistant.helpers.entity import EntityCategory


async def test_setup_creates_5_select_entities(hass, setup_integration):
    states = hass.states.async_all("select")
    assert len(states) == 5


async def test_select_clean_times_current_option(hass, setup_integration):
    state = hass.states.get("select.aspirador_clean_times")
    assert state is not None
    # clean_times:1 -> "one_time"
    assert state.state == "one_time"


async def test_select_mop_water_level_current_option(hass, setup_integration):
    state = hass.states.get("select.aspirador_mop_water_level")
    # mop_water_level:1 -> "level_1"
    assert state.state == "level_1"


async def test_select_sweep_route(hass, setup_integration):
    state = hass.states.get("select.aspirador_sweep_route")
    # sweep_route:2 -> "daily"
    assert state.state == "daily"


async def test_select_obstacle_avoidance(hass, setup_integration):
    state = hass.states.get("select.aspirador_obstacle_avoidance")
    # 0 -> less_collisions
    assert state.state == "less_collisions"


async def test_select_options_listed(hass, setup_integration):
    state = hass.states.get("select.aspirador_clean_times")
    assert "one_time" in state.attributes["options"]
    assert "two_times" in state.attributes["options"]


async def test_select_entity_category_is_config(hass, setup_integration):
    from homeassistant.helpers.entity_registry import async_get

    er = async_get(hass)
    entry = er.async_get("select.aspirador_clean_times")
    assert entry is not None
    assert entry.entity_category == EntityCategory.CONFIG


async def test_select_option_calls_set_property(
    hass, setup_integration, mock_miot_device
):
    mock_miot_device.set_property_by.reset_mock()
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.aspirador_clean_times", "option": "two_times"},
        blocking=True,
    )
    assert mock_miot_device.set_property_by.called


async def test_select_option_optimistic_update(
    hass, setup_integration, mock_miot_device
):
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.aspirador_sweep_route", "option": "careful"},
        blocking=True,
    )
    state = hass.states.get("select.aspirador_sweep_route")
    assert state.state == "careful"


async def test_select_has_icon(hass, setup_integration):
    state = hass.states.get("select.aspirador_mode")
    assert state.attributes.get("icon") == "mdi:broom"
