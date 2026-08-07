"""Image platform serving the rendered vacuum map (cloud-backed)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..spec import EntityKey  # noqa: TID252
from .map import XiaomiVacuumMap

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..data import XiaomiVacuumConfigEntry  # noqa: TID252

__all__ = ["XiaomiVacuumMap"]

_IMAGE_CLASSES: dict[EntityKey, type[XiaomiVacuumMap]] = {
    EntityKey.MAP_IMAGE: XiaomiVacuumMap,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: XiaomiVacuumConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the map image entity (only when configured & advertised by spec)."""
    map_coord = entry.runtime_data.map_coordinator
    if map_coord is None:
        return
    coordinator = entry.runtime_data.coordinator
    entities = [
        cls(
            hass,
            state_coordinator=coordinator,
            map_coordinator=map_coord,
        )
        for key, cls in _IMAGE_CLASSES.items()
        if key in coordinator.spec.entities
    ]
    async_add_entities(entities)
