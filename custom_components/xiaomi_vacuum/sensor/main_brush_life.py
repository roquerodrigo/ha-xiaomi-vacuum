"""Main-brush remaining-life sensor."""

from __future__ import annotations

from .life_base import _XiaomiVacuumLifeSensor


class XiaomiVacuumMainBrushLifeSensor(_XiaomiVacuumLifeSensor):
    """Remaining life of the main cleaning brush."""

    _attr_translation_key = "main_brush_life"

    _property_name = "main_brush_life"
