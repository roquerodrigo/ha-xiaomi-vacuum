"""Select platform for xiaomi_vacuum."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .clean_times import XiaomiVacuumCleanTimesSelect
from .mop_water_level import XiaomiVacuumMopWaterLevelSelect
from .obstacle_avoidance import XiaomiVacuumObstacleAvoidanceSelect
from .sweep_mop_type import XiaomiVacuumSweepMopTypeSelect
from .sweep_route import XiaomiVacuumSweepRouteSelect

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..data import XiaomiVacuumConfigEntry  # noqa: TID252

__all__ = [
    "XiaomiVacuumCleanTimesSelect",
    "XiaomiVacuumMopWaterLevelSelect",
    "XiaomiVacuumObstacleAvoidanceSelect",
    "XiaomiVacuumSweepMopTypeSelect",
    "XiaomiVacuumSweepRouteSelect",
]


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: XiaomiVacuumConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up all select entities."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        [
            XiaomiVacuumSweepMopTypeSelect(coordinator),
            XiaomiVacuumCleanTimesSelect(coordinator),
            XiaomiVacuumMopWaterLevelSelect(coordinator),
            XiaomiVacuumSweepRouteSelect(coordinator),
            XiaomiVacuumObstacleAvoidanceSelect(coordinator),
        ]
    )
