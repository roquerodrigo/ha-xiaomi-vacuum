"""Binary sensor platform for xiaomi_vacuum."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..spec import EntityKey  # noqa: TID252
from .battery_charging import XiaomiVacuumBatteryChargingSensor
from .mop_pad import XiaomiVacuumMopPadSensor

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..data import XiaomiVacuumConfigEntry  # noqa: TID252

__all__ = [
    "XiaomiVacuumBatteryChargingSensor",
    "XiaomiVacuumMopPadSensor",
]

_BINARY_SENSOR_CLASSES: dict[EntityKey, type] = {
    EntityKey.BATTERY_CHARGING_SENSOR: XiaomiVacuumBatteryChargingSensor,
    EntityKey.MOP_PAD_SENSOR: XiaomiVacuumMopPadSensor,
}


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: XiaomiVacuumConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor entities this model advertises."""
    coordinator = entry.runtime_data.coordinator
    entities = [
        cls(coordinator=coordinator)
        for key, cls in _BINARY_SENSOR_CLASSES.items()
        if key in coordinator.spec.entities
    ]
    async_add_entities(entities)
