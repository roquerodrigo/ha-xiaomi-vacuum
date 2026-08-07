"""Button platform for xiaomi_vacuum."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..spec import EntityKey  # noqa: TID252
from .dust_arrest import XiaomiVacuumDustArrestButton

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..data import XiaomiVacuumConfigEntry  # noqa: TID252
    from ..entity import XiaomiVacuumEntity  # noqa: TID252

__all__ = ["XiaomiVacuumDustArrestButton"]

_BUTTON_CLASSES: dict[EntityKey, type[XiaomiVacuumEntity]] = {
    EntityKey.DUST_ARREST_BUTTON: XiaomiVacuumDustArrestButton,
}


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: XiaomiVacuumConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button entities this model advertises (capability-gated)."""
    coordinator = entry.runtime_data.coordinator
    entities = [
        cls(coordinator=coordinator)
        for key, cls in _BUTTON_CLASSES.items()
        if key in coordinator.spec.entities
    ]
    async_add_entities(entities)
