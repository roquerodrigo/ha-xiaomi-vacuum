"""Main-brush hours-left sensor."""

from __future__ import annotations

from ..spec import Property  # noqa: TID252
from .time_left_base import _XiaomiVacuumTimeLeftSensor


class XiaomiVacuumMainBrushTimeLeftSensor(_XiaomiVacuumTimeLeftSensor):
    """Hours left on the main brush."""

    _attr_translation_key = "main_brush_time_left"

    _property_name = Property.MAIN_BRUSH_TIME_LEFT
