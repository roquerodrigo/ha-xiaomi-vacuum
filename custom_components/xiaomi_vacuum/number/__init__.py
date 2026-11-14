"""Number platform for xiaomi_vacuum."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..spec import EntityKey  # noqa: TID252
from .mop_wash_time_interval import XiaomiVacuumMopWashTimeIntervalNumber
from .volume import XiaomiVacuumVolumeNumber

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..data import XiaomiVacuumConfigEntry  # noqa: TID252
    from ..entity import XiaomiVacuumEntity  # noqa: TID252

__all__ = [
    "XiaomiVacuumMopWashTimeIntervalNumber",
    "XiaomiVacuumVolumeNumber",
]

_NUMBER_CLASSES: dict[EntityKey, type[XiaomiVacuumEntity]] = {
    EntityKey.VOLUME_NUMBER: XiaomiVacuumVolumeNumber,
    EntityKey.MOP_WASH_TIME_INTERVAL_NUMBER: XiaomiVacuumMopWashTimeIntervalNumber,
}


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: XiaomiVacuumConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number entities this model advertises (spec-gated)."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        cls(coordinator)
        for key, cls in _NUMBER_CLASSES.items()
        if key in coordinator.spec.entities
    )
