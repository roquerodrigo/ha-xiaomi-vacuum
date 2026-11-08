"""Value tables the supported models publish identically."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

FAN_SPEEDS: Mapping[str, int] = MappingProxyType(
    {
        "silent": 1,
        "basic": 2,
        "strong": 3,
        "full_speed": 4,
    }
)

SWEEP_MOP_TYPES: Mapping[str, int] = MappingProxyType(
    {
        "sweep": 1,
        "mop": 2,
        "sweep_mop": 3,
        "sweep_before_mopping": 4,
    }
)

CLEAN_TIMES: Mapping[str, int] = MappingProxyType(
    {
        "one_time": 1,
        "two_times": 2,
    }
)

CHARGING_STATE_SLUGS: Mapping[int, str] = MappingProxyType(
    {
        1: "charging",
        2: "not_charging",
        3: "not_chargeable",
    }
)

SWEEP_ROUTES: Mapping[str, int] = MappingProxyType(
    {
        "quick": 1,
        "daily": 2,
        "careful": 3,
    }
)

OBSTACLE_AVOIDANCES: Mapping[str, int] = MappingProxyType(
    {
        "less_collisions": 0,
        "high_coverage": 1,
    }
)
