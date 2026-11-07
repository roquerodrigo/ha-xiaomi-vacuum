"""Button platform for xiaomi_vacuum."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..spec import EntityKey  # noqa: TID252
from .dust_arrest import XiaomiVacuumDustArrestButton
from .reset_filter import XiaomiVacuumResetFilterButton
from .reset_main_brush import XiaomiVacuumResetMainBrushButton
from .reset_mop import XiaomiVacuumResetMopButton
from .reset_side_brush import XiaomiVacuumResetSideBrushButton
from .start_dry import XiaomiVacuumStartDryButton
from .start_mop_wash import XiaomiVacuumStartMopWashButton
from .stop_dry import XiaomiVacuumStopDryButton
from .stop_mop_wash import XiaomiVacuumStopMopWashButton

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..data import XiaomiVacuumConfigEntry  # noqa: TID252
    from ..entity import XiaomiVacuumEntity  # noqa: TID252

__all__ = [
    "XiaomiVacuumDustArrestButton",
    "XiaomiVacuumResetFilterButton",
    "XiaomiVacuumResetMainBrushButton",
    "XiaomiVacuumResetMopButton",
    "XiaomiVacuumResetSideBrushButton",
    "XiaomiVacuumStartDryButton",
    "XiaomiVacuumStartMopWashButton",
    "XiaomiVacuumStopDryButton",
    "XiaomiVacuumStopMopWashButton",
]

_BUTTON_CLASSES: dict[EntityKey, type[XiaomiVacuumEntity]] = {
    EntityKey.DUST_ARREST_BUTTON: XiaomiVacuumDustArrestButton,
    EntityKey.RESET_FILTER_BUTTON: XiaomiVacuumResetFilterButton,
    EntityKey.RESET_MAIN_BRUSH_BUTTON: XiaomiVacuumResetMainBrushButton,
    EntityKey.RESET_MOP_BUTTON: XiaomiVacuumResetMopButton,
    EntityKey.RESET_SIDE_BRUSH_BUTTON: XiaomiVacuumResetSideBrushButton,
    EntityKey.START_DRY_BUTTON: XiaomiVacuumStartDryButton,
    EntityKey.START_MOP_WASH_BUTTON: XiaomiVacuumStartMopWashButton,
    EntityKey.STOP_DRY_BUTTON: XiaomiVacuumStopDryButton,
    EntityKey.STOP_MOP_WASH_BUTTON: XiaomiVacuumStopMopWashButton,
}


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: XiaomiVacuumConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button entities this model advertises (spec-gated)."""
    coordinator = entry.runtime_data.coordinator
    entities = [
        cls(coordinator=coordinator)
        for key, cls in _BUTTON_CLASSES.items()
        if key in coordinator.spec.entities
    ]
    async_add_entities(entities)
