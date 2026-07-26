"""Obstacle-avoidance select entity (X20 Max only)."""

from __future__ import annotations

from ..spec import OBSTACLE_AVOIDANCES  # noqa: TID252
from .base import _XiaomiVacuumSelect


class XiaomiVacuumObstacleAvoidanceSelect(_XiaomiVacuumSelect):
    """
    Select the obstacle-avoidance strategy.

    Only created for models whose spec advertises ``has_obstacle_avoidance``
    (the X20 Max); the S20+ has no such property.
    """

    _attr_translation_key = "obstacle_avoidance_strategy"
    _attr_icon = "mdi:shield-car"

    _property_name = "obstacle_avoidance_strategy"

    @property
    def _slug_to_value(self) -> dict[str, int]:
        return dict(OBSTACLE_AVOIDANCES)
