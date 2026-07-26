"""Sweep-route select entity (X20 Max only)."""

from __future__ import annotations

from ..spec import SWEEP_ROUTES  # noqa: TID252
from .base import _XiaomiVacuumSelect


class XiaomiVacuumSweepRouteSelect(_XiaomiVacuumSelect):
    """
    Select the route pattern the vacuum follows while cleaning.

    Only created for models whose spec advertises ``has_sweep_route``
    (the X20 Max); the S20+ has no such property.
    """

    _attr_translation_key = "sweep_route"
    _attr_icon = "mdi:map-marker-path"

    _property_name = "sweep_route"

    @property
    def _slug_to_value(self) -> dict[str, int]:
        return dict(SWEEP_ROUTES)
