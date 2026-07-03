from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass


async def test_battery_charging_on(hass, setup_integration):
    state = hass.states.get("binary_sensor.aspirador_charging")
    assert state is not None
    # SAMPLE_STATE has charging_state:1 -> charging
    assert state.state == "on"
    assert state.attributes["device_class"] == BinarySensorDeviceClass.BATTERY_CHARGING


async def test_battery_charging_off(hass, setup_integration):
    coordinator = setup_integration.runtime_data.coordinator
    coordinator.async_set_updated_data({**coordinator.data, "charging_state": 2})
    await hass.async_block_till_done()
    state = hass.states.get("binary_sensor.aspirador_charging")
    assert state.state == "off"


async def test_battery_charging_unknown(hass, setup_integration):
    coordinator = setup_integration.runtime_data.coordinator
    data = dict(coordinator.data)
    data.pop("charging_state", None)
    coordinator.async_set_updated_data(data)
    await hass.async_block_till_done()
    state = hass.states.get("binary_sensor.aspirador_charging")
    assert state.state == "unknown"
