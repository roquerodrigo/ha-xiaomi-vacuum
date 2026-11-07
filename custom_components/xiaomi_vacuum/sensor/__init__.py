"""Sensor platform for xiaomi_vacuum."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..spec import EntityKey  # noqa: TID252
from .battery import XiaomiVacuumBatterySensor
from .drying_time_left import XiaomiVacuumDryingTimeLeftSensor
from .error import XiaomiVacuumErrorSensor
from .error_code import XiaomiVacuumErrorCodeSensor
from .filter_life import XiaomiVacuumFilterLifeSensor
from .filter_time_left import XiaomiVacuumFilterTimeLeftSensor
from .main_brush_life import XiaomiVacuumMainBrushLifeSensor
from .main_brush_time_left import XiaomiVacuumMainBrushTimeLeftSensor
from .mop_life import XiaomiVacuumMopLifeSensor
from .mop_time_left import XiaomiVacuumMopTimeLeftSensor
from .side_brush_life import XiaomiVacuumSideBrushLifeSensor
from .side_brush_time_left import XiaomiVacuumSideBrushTimeLeftSensor
from .status import XiaomiVacuumStatusSensor
from .total_clean_area import XiaomiVacuumTotalCleanAreaSensor
from .total_clean_count import XiaomiVacuumTotalCleanCountSensor
from .total_clean_time import XiaomiVacuumTotalCleanTimeSensor

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..data import XiaomiVacuumConfigEntry  # noqa: TID252
    from ..entity import XiaomiVacuumEntity  # noqa: TID252

__all__ = [
    "XiaomiVacuumBatterySensor",
    "XiaomiVacuumDryingTimeLeftSensor",
    "XiaomiVacuumErrorCodeSensor",
    "XiaomiVacuumErrorSensor",
    "XiaomiVacuumFilterLifeSensor",
    "XiaomiVacuumFilterTimeLeftSensor",
    "XiaomiVacuumMainBrushLifeSensor",
    "XiaomiVacuumMainBrushTimeLeftSensor",
    "XiaomiVacuumMopLifeSensor",
    "XiaomiVacuumMopTimeLeftSensor",
    "XiaomiVacuumSideBrushLifeSensor",
    "XiaomiVacuumSideBrushTimeLeftSensor",
    "XiaomiVacuumStatusSensor",
    "XiaomiVacuumTotalCleanAreaSensor",
    "XiaomiVacuumTotalCleanCountSensor",
    "XiaomiVacuumTotalCleanTimeSensor",
]

_SENSOR_CLASSES: dict[EntityKey, type[XiaomiVacuumEntity]] = {
    EntityKey.BATTERY_SENSOR: XiaomiVacuumBatterySensor,
    EntityKey.STATUS_SENSOR: XiaomiVacuumStatusSensor,
    EntityKey.ERROR_SENSOR: XiaomiVacuumErrorSensor,
    EntityKey.ERROR_CODE_SENSOR: XiaomiVacuumErrorCodeSensor,
    EntityKey.MOP_LIFE_SENSOR: XiaomiVacuumMopLifeSensor,
    EntityKey.MAIN_BRUSH_LIFE_SENSOR: XiaomiVacuumMainBrushLifeSensor,
    EntityKey.SIDE_BRUSH_LIFE_SENSOR: XiaomiVacuumSideBrushLifeSensor,
    EntityKey.FILTER_LIFE_SENSOR: XiaomiVacuumFilterLifeSensor,
    EntityKey.DRYING_TIME_LEFT_SENSOR: XiaomiVacuumDryingTimeLeftSensor,
    EntityKey.FILTER_TIME_LEFT_SENSOR: XiaomiVacuumFilterTimeLeftSensor,
    EntityKey.MAIN_BRUSH_TIME_LEFT_SENSOR: XiaomiVacuumMainBrushTimeLeftSensor,
    EntityKey.MOP_TIME_LEFT_SENSOR: XiaomiVacuumMopTimeLeftSensor,
    EntityKey.SIDE_BRUSH_TIME_LEFT_SENSOR: XiaomiVacuumSideBrushTimeLeftSensor,
    EntityKey.TOTAL_CLEAN_AREA_SENSOR: XiaomiVacuumTotalCleanAreaSensor,
    EntityKey.TOTAL_CLEAN_COUNT_SENSOR: XiaomiVacuumTotalCleanCountSensor,
    EntityKey.TOTAL_CLEAN_TIME_SENSOR: XiaomiVacuumTotalCleanTimeSensor,
}


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: XiaomiVacuumConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor entities this model advertises."""
    coordinator = entry.runtime_data.coordinator
    entities = [
        cls(coordinator=coordinator)
        for key, cls in _SENSOR_CLASSES.items()
        if key in coordinator.spec.entities
    ]
    async_add_entities(entities)
