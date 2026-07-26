"""Sweep/mop type select entity."""

from __future__ import annotations

from .base import _XiaomiVacuumSelect


class XiaomiVacuumSweepMopTypeSelect(_XiaomiVacuumSelect):
    """Select the sweep/mop type the vacuum uses while cleaning."""

    _attr_translation_key = "sweep_mop_type"
    _attr_icon = "mdi:broom"

    _property_name = "sweep_mop_type"

    @property
    def _slug_to_value(self) -> dict[str, int]:
        return dict(self.coordinator.spec.sweep_mop_types)
