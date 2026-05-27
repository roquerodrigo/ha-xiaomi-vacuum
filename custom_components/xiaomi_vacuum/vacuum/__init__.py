"""Vacuum platform for xiaomi_vacuum."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .cleaner import XiaomiVacuum

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..data import XiaomiVacuumConfigEntry  # noqa: TID252

__all__ = ["XiaomiVacuum"]


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: XiaomiVacuumConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the vacuum entity."""
    async_add_entities([XiaomiVacuum(coordinator=entry.runtime_data.coordinator)])
