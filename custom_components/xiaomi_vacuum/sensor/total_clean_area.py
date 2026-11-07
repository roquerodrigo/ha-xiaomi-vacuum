"""Lifetime cleaned-area sensor."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfArea

from ..spec import Property  # noqa: TID252
from .property_base import _XiaomiVacuumPropertySensor


class XiaomiVacuumTotalCleanAreaSensor(_XiaomiVacuumPropertySensor):
    """Area cleaned over the vacuum's life, updated when it docks."""

    _attr_translation_key = "total_clean_area"
    _attr_device_class = SensorDeviceClass.AREA
    _attr_native_unit_of_measurement = UnitOfArea.SQUARE_METERS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    _property_name = Property.TOTAL_CLEAN_AREA
