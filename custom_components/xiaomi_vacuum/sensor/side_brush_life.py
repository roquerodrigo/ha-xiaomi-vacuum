"""Side-brush remaining-life sensor."""

from __future__ import annotations

from .life_base import _XiaomiVacuumLifeSensor


class XiaomiVacuumSideBrushLifeSensor(_XiaomiVacuumLifeSensor):
    """Remaining life of the side cleaning brush."""

    _attr_translation_key = "side_brush_life"
    _attr_icon = "mdi:broom"

    _property_name = "side_brush_life"
