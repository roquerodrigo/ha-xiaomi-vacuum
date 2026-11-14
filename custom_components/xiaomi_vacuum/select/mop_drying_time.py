"""Mop drying time select entity."""

from __future__ import annotations

from ..spec import Property  # noqa: TID252
from .base import _XiaomiVacuumSelect


class XiaomiVacuumMopDryingTimeSelect(_XiaomiVacuumSelect):
    """Select how long the dock dries the mop pads."""

    _attr_translation_key = "mop_drying_time"

    _property_name = Property.MOP_DRYING_TIME

    @property
    def _slug_to_value(self) -> dict[str, int]:
        return dict(self.coordinator.spec.mop_drying_times)
