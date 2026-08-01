"""Sensor platform for xiaomi_vacuum."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..spec import EntityKey  # noqa: TID252
from .battery import XiaomiVacuumBatterySensor
from .error import XiaomiVacuumErrorSensor
from .error_code import XiaomiVacuumErrorCodeSensor
from .filter_life import XiaomiVacuumFilterLifeSensor
from .main_brush_life import XiaomiVacuumMainBrushLifeSensor
from .mop_life import XiaomiVacuumMopLifeSensor
from .side_brush_life import XiaomiVacuumSideBrushLifeSensor
from .status import XiaomiVacuumStatusSensor

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..data import XiaomiVacuumConfigEntry  # noqa: TID252

__all__ = [
    "XiaomiVacuumBatterySensor",
    "XiaomiVacuumErrorCodeSensor",
    "XiaomiVacuumErrorSensor",
    "XiaomiVacuumFilterLifeSensor",
    "XiaomiVacuumMainBrushLifeSensor",
    "XiaomiVacuumMopLifeSensor",
    "XiaomiVacuumSideBrushLifeSensor",
    "XiaomiVacuumStatusSensor",
]

_SENSOR_CLASSES: dict[EntityKey, type] = {
    EntityKey.BATTERY_SENSOR: XiaomiVacuumBatterySensor,
    EntityKey.STATUS_SENSOR: XiaomiVacuumStatusSensor,
    EntityKey.ERROR_SENSOR: XiaomiVacuumErrorSensor,
    EntityKey.ERROR_CODE_SENSOR: XiaomiVacuumErrorCodeSensor,
    EntityKey.MOP_LIFE_SENSOR: XiaomiVacuumMopLifeSensor,
    EntityKey.MAIN_BRUSH_LIFE_SENSOR: XiaomiVacuumMainBrushLifeSensor,
    EntityKey.SIDE_BRUSH_LIFE_SENSOR: XiaomiVacuumSideBrushLifeSensor,
    EntityKey.FILTER_LIFE_SENSOR: XiaomiVacuumFilterLifeSensor,
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
