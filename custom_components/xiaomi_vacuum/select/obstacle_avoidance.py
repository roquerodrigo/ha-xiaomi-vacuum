"""Obstacle-avoidance select entity (X20 Max only)."""

from __future__ import annotations

from ..spec import Property  # noqa: TID252
from .base import _XiaomiVacuumSelect


class XiaomiVacuumObstacleAvoidanceSelect(_XiaomiVacuumSelect):
    """
    Select the obstacle-avoidance strategy.

    Only created for models whose spec advertises
    ``Capability.OBSTACLE_AVOIDANCE`` (the X20 Max); the S20+ has no such
    property.
    """

    _attr_translation_key = "obstacle_avoidance_strategy"
    _attr_icon = "mdi:shield-car"

    _property_name = Property.OBSTACLE_AVOIDANCE_STRATEGY

    @property
    def _slug_to_value(self) -> dict[str, int]:
        return dict(self.coordinator.spec.obstacle_avoidances)
