"""Vacuum platform for xiaomi_vacuum."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform

from ..spec import EntityKey  # noqa: TID252
from .cleaner import XiaomiVacuum

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..data import XiaomiVacuumConfigEntry  # noqa: TID252

__all__ = ["XiaomiVacuum"]

SERVICE_CLEAN_ZONE = "clean_zone"
SERVICE_START_CUSTOM_CLEANING = "start_custom_cleaning"

_ZONE_CORNERS = vol.ExactSequence([vol.Coerce(int)] * 4)

CLEAN_ZONE_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required("zones"): vol.All(
            cv.ensure_list, vol.Length(min=1), [vol.All(list, _ZONE_CORNERS, list)]
        ),
        vol.Optional("repeats"): vol.All(vol.Coerce(int), vol.Range(min=1)),
    }
)

START_CUSTOM_CLEANING_SCHEMA = cv.make_entity_service_schema(
    {vol.Required("name"): vol.All(cv.string, vol.Length(min=1))}
)

_VACUUM_CLASSES: dict[EntityKey, type[XiaomiVacuum]] = {
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
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_CLEAN_ZONE, CLEAN_ZONE_SCHEMA, "async_clean_zone"
    )
    platform.async_register_entity_service(
        SERVICE_START_CUSTOM_CLEANING,
        START_CUSTOM_CLEANING_SCHEMA,
        "async_start_custom_cleaning",
    )
