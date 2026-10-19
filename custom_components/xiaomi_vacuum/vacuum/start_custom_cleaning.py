"""The start_custom_cleaning action, offering the saved cleanings as options."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_set_service_schema

from ..api import XiaomiVacuumApiClientError  # noqa: TID252
from ..const import DOMAIN, LOGGER  # noqa: TID252

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ..api import CustomCleaning  # noqa: TID252
    from ..data import XiaomiVacuumConfigEntry  # noqa: TID252

SERVICE_START_CUSTOM_CLEANING = "start_custom_cleaning"

START_CUSTOM_CLEANING_SCHEMA = cv.make_entity_service_schema(
    {vol.Required("name"): vol.All(cv.string, vol.Length(min=1))}
)


async def async_refresh_custom_cleaning_options(
    hass: HomeAssistant, entry: XiaomiVacuumConfigEntry
) -> None:
    """Read the vacuum's custom cleanings when it is reachable and offer them."""
    data = entry.runtime_data
    if data.spec.user_define_sweep_config is None:
        return
    if not data.coordinator.last_update_success:
        return
    try:
        cleanings = await data.client.async_get_custom_cleanings()
    except XiaomiVacuumApiClientError as exception:
        LOGGER.warning("Failed to read custom cleanings: %s", exception)
        return
    async_update_custom_cleaning_options(hass, entry, cleanings)


@callback
def async_update_custom_cleaning_options(
    hass: HomeAssistant,
    entry: XiaomiVacuumConfigEntry,
    cleanings: Sequence[CustomCleaning],
) -> None:
    """
    Offer the custom cleanings of every vacuum as the action's name options.

    services.yaml cannot list options that live on the device, so the
    description is replaced at runtime, the way the script integration
    describes each script's fields.
    """
    entry.runtime_data.custom_cleanings = tuple(cleanings)
    entries = {
        loaded.entry_id: loaded
        for loaded in hass.config_entries.async_loaded_entries(DOMAIN)
    }
    entries[entry.entry_id] = entry
    names = list(
        dict.fromkeys(
            cleaning.name
            for each_entry in entries.values()
            for cleaning in each_entry.runtime_data.custom_cleanings
        )
    )
    async_set_service_schema(
        hass,
        DOMAIN,
        SERVICE_START_CUSTOM_CLEANING,
        {
            "fields": {
                "name": {
                    "required": True,
                    "selector": {"select": {"options": names, "custom_value": True}},
                }
            },
            "target": {"entity": {"integration": DOMAIN, "domain": "vacuum"}},
        },
    )
