"""Lifetime cleaning-count sensor."""

from __future__ import annotations

from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import EntityCategory

from ..spec import Property  # noqa: TID252
from .property_base import _XiaomiVacuumPropertySensor


class XiaomiVacuumTotalCleanCountSensor(_XiaomiVacuumPropertySensor):
    """Number of cleaning jobs over the vacuum's life."""

    _attr_translation_key = "total_clean_count"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    _property_name = Property.TOTAL_CLEAN_COUNT
