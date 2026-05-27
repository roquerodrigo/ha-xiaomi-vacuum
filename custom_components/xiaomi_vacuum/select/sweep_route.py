"""Sweep-route select entity."""

from __future__ import annotations

from typing import ClassVar

from ..const import SWEEP_ROUTE_NAMES, SWEEP_ROUTES  # noqa: TID252
from .base import _XiaomiVacuumSelect


class XiaomiVacuumSweepRouteSelect(_XiaomiVacuumSelect):
    """Select the route pattern the vacuum follows while cleaning."""

    _attr_translation_key = "sweep_route"
    _attr_icon = "mdi:map-marker-path"
    _attr_options: ClassVar[list[str]] = list(SWEEP_ROUTES)

    _property_name = "sweep_route"
    _slug_to_value: ClassVar[dict[str, int]] = SWEEP_ROUTES
    _value_to_slug: ClassVar[dict[int, str]] = SWEEP_ROUTE_NAMES
