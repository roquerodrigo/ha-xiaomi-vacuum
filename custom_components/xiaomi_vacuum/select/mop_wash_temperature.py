"""Mop wash temperature select entity."""

from __future__ import annotations

from ..spec import Property  # noqa: TID252
from .base import _XiaomiVacuumSelect


class XiaomiVacuumMopWashTemperatureSelect(_XiaomiVacuumSelect):
    """Select the temperature of the water the dock washes the mop with."""

    _attr_translation_key = "mop_wash_temperature"

    _property_name = Property.MOP_WASH_TEMPERATURE

    @property
    def _slug_to_value(self) -> dict[str, int]:
        return dict(self.coordinator.spec.mop_wash_temperatures)
