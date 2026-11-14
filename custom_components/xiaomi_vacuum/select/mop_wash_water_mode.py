"""Mop wash water mode select entity."""

from __future__ import annotations

from ..spec import Property  # noqa: TID252
from .base import _XiaomiVacuumSelect


class XiaomiVacuumMopWashWaterModeSelect(_XiaomiVacuumSelect):
    """Select how much water the dock uses to wash the mop."""

    _attr_translation_key = "mop_wash_water_mode"

    _property_name = Property.MOP_WASH_WATER_MODE

    @property
    def _slug_to_value(self) -> dict[str, int]:
        return dict(self.coordinator.spec.mop_wash_water_modes)
