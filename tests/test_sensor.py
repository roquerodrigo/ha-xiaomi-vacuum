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


async def test_error_sensor_ok_when_no_fault(hass, setup_integration):
    state = hass.states.get("sensor.aspirador_error")
    assert state is not None
    # sample_state has fault == 0 -> healthy
    assert state.state == "OK"
    assert state.attributes["fault_code"] == 0


async def test_error_sensor_shows_localized_cloud_text(hass, setup_integration):
    coordinator = setup_integration.runtime_data.coordinator
    data = dict(coordinator.data)
    data["fault"] = 210009
    data["fault_text"] = "Não foi possível voltar à base para carregar."
    coordinator.async_set_updated_data(data)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.aspirador_error")
    assert state.state == "Não foi possível voltar à base para carregar."
    assert state.attributes["fault_code"] == 210009


async def test_error_sensor_falls_back_to_code(hass, setup_integration):
    coordinator = setup_integration.runtime_data.coordinator
    data = dict(coordinator.data)
    data["fault"] = 210009
    data.pop("fault_text", None)
    coordinator.async_set_updated_data(data)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.aspirador_error")
    assert state.state == "Error 210009"


async def test_consumable_life_sensors(hass, setup_integration):
    for eid, expected in (
        ("sensor.aspirador_mop_life", "85"),
        ("sensor.aspirador_main_brush_life", "71"),
        ("sensor.aspirador_side_brush_life", "90"),
        ("sensor.aspirador_filter_life", "70"),
    ):
        state = hass.states.get(eid)
        assert state is not None, eid
        assert state.state == expected
        assert state.attributes["unit_of_measurement"] == PERCENTAGE


async def test_status_sensor(hass, setup_integration):
    state = hass.states.get("sensor.aspirador_status")
    assert state is not None
    # SAMPLE_STATE has status:2 -> "charging"
    assert state.state == "charging"
    assert state.attributes["device_class"] == SensorDeviceClass.ENUM
    assert "sweeping" in state.attributes["options"]

    coordinator = setup_integration.runtime_data.coordinator
    coordinator.async_set_updated_data({**coordinator.data, "status": 5})
    await hass.async_block_till_done()
    assert hass.states.get("sensor.aspirador_status").state == "paused"


async def test_status_sensor_unknown_code(hass, setup_integration):
    coordinator = setup_integration.runtime_data.coordinator
    # an unmapped status code -> None (HA reports "unknown")
    coordinator.async_set_updated_data({**coordinator.data, "status": 999})
    await hass.async_block_till_done()
    assert hass.states.get("sensor.aspirador_status").state in (
        "unknown",
        "unavailable",
    )


async def test_error_code_sensor(hass, setup_integration):
    # healthy -> 0
    state = hass.states.get("sensor.aspirador_error_code")
    assert state is not None
    assert state.state == "0"

    coordinator = setup_integration.runtime_data.coordinator
    coordinator.async_set_updated_data({**coordinator.data, "fault": 210009})
    await hass.async_block_till_done()
    assert hass.states.get("sensor.aspirador_error_code").state == "210009"
