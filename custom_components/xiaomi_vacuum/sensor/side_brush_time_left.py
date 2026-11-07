"""Side-brush hours-left sensor."""

from __future__ import annotations

from ..spec import Property  # noqa: TID252
from .time_left_base import _XiaomiVacuumTimeLeftSensor


class XiaomiVacuumSideBrushTimeLeftSensor(_XiaomiVacuumTimeLeftSensor):
    """Hours left on the side brush."""

    _attr_translation_key = "side_brush_time_left"

    _property_name = Property.SIDE_BRUSH_TIME_LEFT
