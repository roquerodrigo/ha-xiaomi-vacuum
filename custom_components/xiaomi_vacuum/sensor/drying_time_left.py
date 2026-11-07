"""Mop-pad drying time-left sensor."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTime

from ..spec import Property  # noqa: TID252
from .property_base import _XiaomiVacuumPropertySensor


class XiaomiVacuumDryingTimeLeftSensor(_XiaomiVacuumPropertySensor):
    """Minutes the dock keeps drying the mop pads; 0 when it is not drying."""

    _attr_translation_key = "drying_time_left"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_state_class = SensorStateClass.MEASUREMENT

    _property_name = Property.DRYING_TIME_LEFT
