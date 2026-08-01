"""End-to-end behaviour for the S20+ (xiaomi.vacuum.b108gl) model.

These exercise the per-model spec selection through the real setup flow: the
S20+ must NOT get the sweep-route / obstacle-avoidance selects or the
dust-arrest button (it has none of that hardware), and its return-home command
must target the battery.start-charge action instead of the vacuum service.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState

from custom_components.xiaomi_vacuum.spec import Capability


async def test_b108_setup_loads(hass, setup_integration_b108):
    assert setup_integration_b108.state == ConfigEntryState.LOADED


async def test_b108_picks_the_right_spec(hass, setup_integration_b108):
    spec = setup_integration_b108.runtime_data.spec
    assert spec.model == "xiaomi.vacuum.b108gl"
    assert spec.fault_kind == "simple"
    assert Capability.DUST_ARREST not in spec.capabilities
    assert Capability.SWEEP_ROUTE not in spec.capabilities
    assert Capability.OBSTACLE_AVOIDANCE not in spec.capabilities


async def test_b108_creates_only_three_selects(hass, setup_integration_b108):
    """No sweep-route / obstacle-avoidance selects on the S20+."""
    states = hass.states.async_all("select")
    entity_ids = {s.entity_id for s in states}
    assert len(states) == 3
    # ``translation_key`` is entity metadata, not state data, so it never appears
    # in ``state.attributes`` — assert on entity ids instead, which carry it.
    assert not any("sweep_route" in e or "obstacle_avoidance" in e for e in entity_ids)


async def test_b108_has_no_dust_arrest_button(hass, setup_integration_b108):
    """The X20 Max auto-dust dock button must not be created on the S20+."""
    buttons = hass.states.async_all("button")
    assert buttons == []


async def test_b108_mop_water_exposes_off_option(hass, setup_integration_b108):
    """S20+ exposes an explicit 'off' (0) mop-water level that the X20 Max lacks."""
    select = hass.states.get("select.sala_s20_mop_water_level")
    assert select is not None
    assert "off" in select.attributes["options"]


async def test_b108_return_home_uses_battery_service(
    hass, setup_integration_b108, mock_miot_device_b108
):
    mock_miot_device_b108.call_action_by.reset_mock()
    await hass.services.async_call(
        "vacuum",
        "return_to_base",
        {"entity_id": "vacuum.sala_s20"},
        blocking=True,
    )
    # S20+ return-home = battery.start-charge = SIID 3 / aiid 1.
    mock_miot_device_b108.call_action_by.assert_any_call(3, 1)


async def test_b108_send_command_has_no_mop_wash_commands(hass, setup_integration_b108):
    """The mop-wash / dry send_commands don't exist on the S20+ whitelist."""
    spec = setup_integration_b108.runtime_data.spec
    assert "start_mop_wash" not in spec.send_commands
    assert "start_dry" not in spec.send_commands
