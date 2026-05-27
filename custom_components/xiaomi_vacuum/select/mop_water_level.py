"""Mop water-level select entity."""

from __future__ import annotations

from typing import ClassVar

from ..const import MOP_WATER_LEVEL_NAMES, MOP_WATER_LEVELS  # noqa: TID252
from .base import _XiaomiVacuumSelect


class XiaomiVacuumMopWaterLevelSelect(_XiaomiVacuumSelect):
    """Select the water level used while mopping."""

    _attr_translation_key = "mop_water_level"
    _attr_icon = "mdi:water-percent"

    _property_name = "mop_water_level"
    _slug_to_value: ClassVar[dict[str, int]] = MOP_WATER_LEVELS
    _value_to_slug: ClassVar[dict[int, str]] = MOP_WATER_LEVEL_NAMES
