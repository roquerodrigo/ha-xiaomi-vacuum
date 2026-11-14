"""Mop wash area interval select entity."""

from __future__ import annotations

from ..spec import Property  # noqa: TID252
from .base import _XiaomiVacuumSelect


class XiaomiVacuumMopWashAreaIntervalSelect(_XiaomiVacuumSelect):
    """Select how many square metres are mopped between two washes."""

    _attr_translation_key = "mop_wash_area_interval"

    _property_name = Property.MOP_WASH_AREA_INTERVAL

    @property
    def _slug_to_value(self) -> dict[str, int]:
        return dict(self.coordinator.spec.mop_wash_area_intervals)
