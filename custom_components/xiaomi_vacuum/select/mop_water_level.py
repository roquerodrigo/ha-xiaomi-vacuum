"""Mop-water-level select entity."""

from __future__ import annotations

from .base import _XiaomiVacuumSelect


class XiaomiVacuumMopWaterLevelSelect(_XiaomiVacuumSelect):
    """
    Select the mop water output level.

    The S20+ (b108gl) exposes an extra "off" (0) level that the X20 Max lacks;
    the option list comes from the active model's spec so it matches the device.
    """

    _attr_translation_key = "mop_water_level"
    _attr_icon = "mdi:water"

    _property_name = "mop_water_level"

    @property
    def _slug_to_value(self) -> dict[str, int]:
        return dict(self.coordinator.spec.mop_water_levels)
