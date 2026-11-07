"""Filter hours-left sensor."""

from __future__ import annotations

from ..spec import Property  # noqa: TID252
from .time_left_base import _XiaomiVacuumTimeLeftSensor


class XiaomiVacuumFilterTimeLeftSensor(_XiaomiVacuumTimeLeftSensor):
    """Hours left on the dust-bin filter."""

    _attr_translation_key = "filter_time_left"

    _property_name = Property.FILTER_TIME_LEFT
