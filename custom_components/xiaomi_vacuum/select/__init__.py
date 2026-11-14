"""Select platform for xiaomi_vacuum."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..spec import EntityKey  # noqa: TID252
from .clean_times import XiaomiVacuumCleanTimesSelect
from .mop_drying_time import XiaomiVacuumMopDryingTimeSelect
from .mop_wash_area_interval import XiaomiVacuumMopWashAreaIntervalSelect
from .mop_wash_frequency import XiaomiVacuumMopWashFrequencySelect
from .mop_water_level import XiaomiVacuumMopWaterLevelSelect
from .obstacle_avoidance import XiaomiVacuumObstacleAvoidanceSelect
from .sweep_mop_type import XiaomiVacuumSweepMopTypeSelect
from .sweep_route import XiaomiVacuumSweepRouteSelect

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..data import XiaomiVacuumConfigEntry  # noqa: TID252
    from ..entity import XiaomiVacuumEntity  # noqa: TID252

__all__ = [
    "XiaomiVacuumCleanTimesSelect",
    "XiaomiVacuumMopDryingTimeSelect",
    "XiaomiVacuumMopWashAreaIntervalSelect",
    "XiaomiVacuumMopWashFrequencySelect",
    "XiaomiVacuumMopWaterLevelSelect",
    "XiaomiVacuumObstacleAvoidanceSelect",
    "XiaomiVacuumSweepMopTypeSelect",
    "XiaomiVacuumSweepRouteSelect",
]

_SELECT_CLASSES: dict[EntityKey, type[XiaomiVacuumEntity]] = {
    EntityKey.SWEEP_MOP_TYPE_SELECT: XiaomiVacuumSweepMopTypeSelect,
    EntityKey.CLEAN_TIMES_SELECT: XiaomiVacuumCleanTimesSelect,
    EntityKey.MOP_WATER_LEVEL_SELECT: XiaomiVacuumMopWaterLevelSelect,
    EntityKey.SWEEP_ROUTE_SELECT: XiaomiVacuumSweepRouteSelect,
    EntityKey.OBSTACLE_AVOIDANCE_SELECT: XiaomiVacuumObstacleAvoidanceSelect,
    EntityKey.MOP_WASH_FREQUENCY_SELECT: XiaomiVacuumMopWashFrequencySelect,
    EntityKey.MOP_WASH_AREA_INTERVAL_SELECT: XiaomiVacuumMopWashAreaIntervalSelect,
    EntityKey.MOP_DRYING_TIME_SELECT: XiaomiVacuumMopDryingTimeSelect,
}


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: XiaomiVacuumConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select entities this model advertises."""
    coordinator = entry.runtime_data.coordinator
    entities = [
        cls(coordinator)
        for key, cls in _SELECT_CLASSES.items()
        if key in coordinator.spec.entities
    ]
    async_add_entities(entities)
