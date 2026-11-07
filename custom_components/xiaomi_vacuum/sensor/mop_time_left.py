"""Mop hours-left sensor."""

from __future__ import annotations

from ..spec import Property  # noqa: TID252
from .time_left_base import _XiaomiVacuumTimeLeftSensor


class XiaomiVacuumMopTimeLeftSensor(_XiaomiVacuumTimeLeftSensor):
    """Hours left on the mop pads."""

    _attr_translation_key = "mop_time_left"

    _property_name = Property.MOP_TIME_LEFT
