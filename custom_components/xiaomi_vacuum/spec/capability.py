"""Optional hardware capabilities that gate entity creation."""

from __future__ import annotations

from enum import StrEnum


class Capability(StrEnum):
    """Model-level capability that gates entity creation on a platform."""

    DUST_ARREST = "dust_arrest"
    SWEEP_ROUTE = "sweep_route"
    OBSTACLE_AVOIDANCE = "obstacle_avoidance"
