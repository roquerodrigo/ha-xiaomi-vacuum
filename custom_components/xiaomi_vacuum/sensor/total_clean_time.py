"""Lifetime cleaning-time sensor."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfTime

from ..spec import Property  # noqa: TID252
from .property_base import _XiaomiVacuumPropertySensor


class XiaomiVacuumTotalCleanTimeSensor(_XiaomiVacuumPropertySensor):
    """Time spent cleaning over the vacuum's life, updated when it docks."""

    _attr_translation_key = "total_clean_time"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_suggested_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    _property_name = Property.TOTAL_CLEAN_TIME
