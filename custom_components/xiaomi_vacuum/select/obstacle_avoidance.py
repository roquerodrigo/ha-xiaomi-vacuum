"""Obstacle-avoidance strategy select entity."""

from __future__ import annotations

from typing import ClassVar

from ..const import OBSTACLE_AVOIDANCE_NAMES, OBSTACLE_AVOIDANCES  # noqa: TID252
from .base import _XiaomiVacuumSelect


class XiaomiVacuumObstacleAvoidanceSelect(_XiaomiVacuumSelect):
    """Select the obstacle-avoidance strategy the vacuum applies."""

    _attr_translation_key = "obstacle_avoidance_strategy"
    _attr_icon = "mdi:radar"

    _property_name = "obstacle_avoidance_strategy"
    _slug_to_value: ClassVar[dict[str, int]] = OBSTACLE_AVOIDANCES
    _value_to_slug: ClassVar[dict[int, str]] = OBSTACLE_AVOIDANCE_NAMES
