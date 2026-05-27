"""Filter remaining-life sensor."""

from __future__ import annotations

from .life_base import _XiaomiVacuumLifeSensor


class XiaomiVacuumFilterLifeSensor(_XiaomiVacuumLifeSensor):
    """Remaining life of the filter."""

    _attr_translation_key = "filter_life"
    _attr_icon = "mdi:air-filter"

    _property_name = "filter_life"
