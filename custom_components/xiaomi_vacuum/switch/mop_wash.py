"""Mop wash switch."""

from __future__ import annotations

from ..spec import Property  # noqa: TID252
from .base import _XiaomiVacuumSwitch


class XiaomiVacuumMopWashSwitch(_XiaomiVacuumSwitch):
    """Washes the mop pads at the dock during a mopping job."""

    _attr_translation_key = "mop_wash"

    _property_name = Property.MOP_WASH
