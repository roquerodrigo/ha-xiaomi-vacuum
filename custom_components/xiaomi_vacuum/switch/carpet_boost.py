"""Carpet-boost switch."""

from __future__ import annotations

from ..spec import Property  # noqa: TID252
from .base import _XiaomiVacuumSwitch


class XiaomiVacuumCarpetBoostSwitch(_XiaomiVacuumSwitch):
    """Raises suction automatically on carpets."""

    _attr_translation_key = "carpet_boost"

    _property_name = Property.CARPET_BOOST
