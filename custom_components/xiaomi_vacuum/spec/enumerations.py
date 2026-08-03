"""Value tables the supported models publish identically."""

from __future__ import annotations

FAN_SPEEDS: dict[str, int] = {
    "silent": 1,
    "basic": 2,
    "strong": 3,
    "full_speed": 4,
}

SWEEP_MOP_TYPES: dict[str, int] = {
    "sweep": 1,
    "mop": 2,
    "sweep_mop": 3,
    "sweep_before_mopping": 4,
}

CLEAN_TIMES: dict[str, int] = {
    "one_time": 1,
    "two_times": 2,
}

CHARGING_STATE_SLUGS: dict[int, str] = {
    1: "charging",
    2: "not_charging",
    3: "not_chargeable",
}

SWEEP_ROUTES: dict[str, int] = {
    "quick": 1,
    "daily": 2,
    "careful": 3,
}

OBSTACLE_AVOIDANCES: dict[str, int] = {
    "less_collisions": 0,
    "high_coverage": 1,
}
