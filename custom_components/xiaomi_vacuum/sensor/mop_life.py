"""Mop remaining-life sensor."""

from __future__ import annotations

from .life_base import _XiaomiVacuumLifeSensor


class XiaomiVacuumMopLifeSensor(_XiaomiVacuumLifeSensor):
    """Remaining life of the mop pad."""

    _attr_translation_key = "mop_life"
    _attr_icon = "mdi:water-percent"

    _property_name = "mop_life"
