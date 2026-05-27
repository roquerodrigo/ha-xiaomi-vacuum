"""Image platform serving the rendered vacuum map (cloud-backed)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .map import XiaomiVacuumMap

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..data import XiaomiVacuumConfigEntry  # noqa: TID252

__all__ = ["XiaomiVacuumMap"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: XiaomiVacuumConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the map image entity (only when the cloud coordinator is configured)."""
    map_coord = entry.runtime_data.map_coordinator
    if map_coord is None:
        return
    async_add_entities(
        [
            XiaomiVacuumMap(
                hass,
                state_coordinator=entry.runtime_data.coordinator,
                map_coordinator=map_coord,
            )
        ]
    )
