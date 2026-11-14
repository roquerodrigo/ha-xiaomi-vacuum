"""Switch platform for xiaomi_vacuum."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..spec import EntityKey  # noqa: TID252
from .auto_dust_collection import XiaomiVacuumAutoDustCollectionSwitch
from .auto_mop_drying import XiaomiVacuumAutoMopDryingSwitch
from .carpet_boost import XiaomiVacuumCarpetBoostSwitch
from .child_lock import XiaomiVacuumChildLockSwitch
from .do_not_disturb import XiaomiVacuumDoNotDisturbSwitch
from .mop_wash import XiaomiVacuumMopWashSwitch
from .resume_after_charge import XiaomiVacuumResumeAfterChargeSwitch

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..data import XiaomiVacuumConfigEntry  # noqa: TID252
    from ..entity import XiaomiVacuumEntity  # noqa: TID252

__all__ = [
    "XiaomiVacuumAutoDustCollectionSwitch",
    "XiaomiVacuumAutoMopDryingSwitch",
    "XiaomiVacuumCarpetBoostSwitch",
    "XiaomiVacuumChildLockSwitch",
    "XiaomiVacuumDoNotDisturbSwitch",
    "XiaomiVacuumMopWashSwitch",
    "XiaomiVacuumResumeAfterChargeSwitch",
]

_SWITCH_CLASSES: dict[EntityKey, type[XiaomiVacuumEntity]] = {
    EntityKey.CHILD_LOCK_SWITCH: XiaomiVacuumChildLockSwitch,
    EntityKey.CARPET_BOOST_SWITCH: XiaomiVacuumCarpetBoostSwitch,
    EntityKey.RESUME_AFTER_CHARGE_SWITCH: XiaomiVacuumResumeAfterChargeSwitch,
    EntityKey.DO_NOT_DISTURB_SWITCH: XiaomiVacuumDoNotDisturbSwitch,
    EntityKey.MOP_WASH_SWITCH: XiaomiVacuumMopWashSwitch,
    EntityKey.AUTO_DUST_COLLECTION_SWITCH: XiaomiVacuumAutoDustCollectionSwitch,
    EntityKey.AUTO_MOP_DRYING_SWITCH: XiaomiVacuumAutoMopDryingSwitch,
}


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: XiaomiVacuumConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch entities this model advertises (spec-gated)."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        cls(coordinator)
        for key, cls in _SWITCH_CLASSES.items()
        if key in coordinator.spec.entities
    )
