"""Sweep-route select entity (X20 Max only)."""

from __future__ import annotations

from ..spec import Property  # noqa: TID252
from .base import _XiaomiVacuumSelect


class XiaomiVacuumSweepRouteSelect(_XiaomiVacuumSelect):
    """Select the route pattern the vacuum follows while cleaning."""

    _attr_translation_key = "sweep_route"

    _property_name = Property.SWEEP_ROUTE

    @property
    def _slug_to_value(self) -> dict[str, int]:
        return dict(self.coordinator.spec.sweep_routes)
