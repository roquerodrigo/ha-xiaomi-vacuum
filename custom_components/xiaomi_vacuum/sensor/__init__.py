"""Sensor platform for xiaomi_vacuum."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .battery import XiaomiVacuumBatterySensor
from .dust_bag_life import XiaomiVacuumDustBagLifeSensor
from .error import XiaomiVacuumErrorSensor
from .error_code import XiaomiVacuumErrorCodeSensor
from .filter_life import XiaomiVacuumFilterLifeSensor
from .mop_life import XiaomiVacuumMopLifeSensor
from .side_brush_life import XiaomiVacuumSideBrushLifeSensor

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..data import XiaomiVacuumConfigEntry  # noqa: TID252

__all__ = [
    "XiaomiVacuumBatterySensor",
    "XiaomiVacuumDustBagLifeSensor",
    "XiaomiVacuumErrorCodeSensor",
    "XiaomiVacuumErrorSensor",
    "XiaomiVacuumFilterLifeSensor",
    "XiaomiVacuumMopLifeSensor",
    "XiaomiVacuumSideBrushLifeSensor",
]


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: XiaomiVacuumConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        [
            XiaomiVacuumBatterySensor(coordinator=coordinator),
            XiaomiVacuumErrorSensor(coordinator=coordinator),
            XiaomiVacuumErrorCodeSensor(coordinator=coordinator),
            XiaomiVacuumMopLifeSensor(coordinator=coordinator),
            XiaomiVacuumSideBrushLifeSensor(coordinator=coordinator),
            XiaomiVacuumFilterLifeSensor(coordinator=coordinator),
            XiaomiVacuumDustBagLifeSensor(coordinator=coordinator),
        ]
    )
