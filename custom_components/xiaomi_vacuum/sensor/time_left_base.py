"""Shared base for consumable hours-left sensors."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfTime

from .property_base import _XiaomiVacuumPropertySensor


class _XiaomiVacuumTimeLeftSensor(_XiaomiVacuumPropertySensor):
    """Hours of use left on a consumable before it should be replaced."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
