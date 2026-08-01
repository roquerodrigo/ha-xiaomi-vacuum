"""Vacuum platform for xiaomi_vacuum."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..spec import EntityKey  # noqa: TID252
from .cleaner import XiaomiVacuum

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..data import XiaomiVacuumConfigEntry  # noqa: TID252

__all__ = ["XiaomiVacuum"]

_VACUUM_CLASSES: dict[EntityKey, type] = {
    EntityKey.VACUUM: XiaomiVacuum,
}


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: XiaomiVacuumConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the vacuum entity this model advertises."""
    coordinator = entry.runtime_data.coordinator
    entities = [
        cls(coordinator=coordinator)
        for key, cls in _VACUUM_CLASSES.items()
        if key in coordinator.spec.entities
    ]
    async_add_entities(entities)
