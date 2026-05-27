"""Xiaomi Vacuum integration for Home Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.loader import async_get_loaded_integration

from .api import XiaomiVacuumApiClient
from .cloud import XiaomiCloud, XiaomiCloudError
from .const import (
    CONF_CLOUD_COUNTRY,
    CONF_CLOUD_SERVICE_TOKEN,
    CONF_CLOUD_SSECURITY,
    CONF_CLOUD_USER_ID,
    CONF_HOST,
    CONF_TOKEN,
    LOGGER,
)
from .coordinator import XiaomiVacuumDataUpdateCoordinator
from .data import XiaomiVacuumData
from .map_coordinator import XiaomiVacuumMapCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import XiaomiVacuumConfigEntry

PLATFORMS: list[Platform] = [
    Platform.VACUUM,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.IMAGE,
    Platform.SENSOR,
]


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
    map_coordinator: XiaomiVacuumMapCoordinator | None = None
    cloud_country = entry.data.get(CONF_CLOUD_COUNTRY)
    ssecurity = entry.data.get(CONF_CLOUD_SSECURITY)
    service_token = entry.data.get(CONF_CLOUD_SERVICE_TOKEN)
    cloud_user_id = entry.data.get(CONF_CLOUD_USER_ID)
    if cloud_country and ssecurity and service_token and cloud_user_id:
        cloud = XiaomiCloud.from_session(
            hass,
            country=cloud_country,
            ssecurity=ssecurity,
            service_token=service_token,
            user_id=cloud_user_id,
        )
        try:
            await cloud.async_resolve_device(entry.data[CONF_TOKEN])
        except XiaomiCloudError as exception:
            LOGGER.warning(
                "Cloud session invalid; reconfigure to refresh: %s", exception
            )
        else:
            coordinator.cloud = cloud
            map_coordinator = XiaomiVacuumMapCoordinator(
                hass, cloud=cloud, state_coordinator=coordinator
            )

    entry.runtime_data = XiaomiVacuumData(
        client=client,
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
        info=info,
        map_coordinator=map_coordinator,
    )

    await coordinator.async_config_entry_first_refresh()
    if map_coordinator is not None:
        await map_coordinator.async_config_entry_first_refresh()

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
