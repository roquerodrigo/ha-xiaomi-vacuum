"""Xiaomi Vacuum integration for Home Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.loader import async_get_loaded_integration

from .api import XiaomiVacuumApiClient
from .const import CONF_HOST, CONF_TOKEN, DOMAIN, LOGGER  # noqa: F401
from .coordinator import XiaomiVacuumDataUpdateCoordinator
from .data import XiaomiVacuumData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import XiaomiVacuumConfigEntry

PLATFORMS: list[Platform] = [Platform.VACUUM, Platform.SELECT, Platform.BUTTON]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: XiaomiVacuumConfigEntry,
) -> bool:
    """Set up Xiaomi Vacuum from a config entry."""
    coordinator = XiaomiVacuumDataUpdateCoordinator(hass=hass)
    client = XiaomiVacuumApiClient(
        hass=hass,
        host=entry.data[CONF_HOST],
        token=entry.data[CONF_TOKEN],
    )
    info = await client.async_get_info()
    LOGGER.debug(
        "Device info: model=%s raw=%s",
        getattr(info, "model", None),
        getattr(info, "raw", None),
    )
    entry.runtime_data = XiaomiVacuumData(
        client=client,
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
        info=info,
    )

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: XiaomiVacuumConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: XiaomiVacuumConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
