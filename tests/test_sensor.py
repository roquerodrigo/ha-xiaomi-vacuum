from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import PERCENTAGE


async def test_battery_sensor_state(hass, setup_integration):
    state = hass.states.get("sensor.aspirador_battery")
    assert state is not None
    assert state.state == "99"


async def test_battery_sensor_attributes(hass, setup_integration):
    state = hass.states.get("sensor.aspirador_battery")
    assert state.attributes["unit_of_measurement"] == PERCENTAGE
    assert state.attributes["device_class"] == SensorDeviceClass.BATTERY
