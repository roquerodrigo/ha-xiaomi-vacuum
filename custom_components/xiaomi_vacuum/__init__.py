"""Xiaomi Vacuum integration for Home Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.loader import async_get_loaded_integration

from .api import XiaomiVacuumApiClient, XiaomiVacuumApiClientCommunicationError
from .cached_device_info import CachedDeviceInfo
from .cloud import XiaomiCloud, XiaomiCloudError
from .const import (
    CONF_CLOUD_COUNTRY,
    CONF_CLOUD_SERVICE_TOKEN,
    CONF_CLOUD_SSECURITY,
    CONF_CLOUD_USER_ID,
    CONF_DEVICE_INFO,
    CONF_HOST,
    CONF_TOKEN,
    LOGGER,
)
from .coordinator import XiaomiVacuumDataUpdateCoordinator
from .data import XiaomiVacuumData
from .map_coordinator import XiaomiVacuumMapCoordinator
from .repairs import async_raise_cannot_connect

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import DeviceInfoLike, JsonObject, XiaomiVacuumConfigEntry

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
    coordinator = XiaomiVacuumDataUpdateCoordinator(hass=hass, config_entry=entry)
    client = XiaomiVacuumApiClient(
        hass=hass,
        host=entry.data[CONF_HOST],
        token=entry.data[CONF_TOKEN],
    )
    offline = False
    info: DeviceInfoLike
    try:
        info = await client.async_get_info()
    except XiaomiVacuumApiClientCommunicationError as exception:
        stored = entry.data.get(CONF_DEVICE_INFO)
        if not stored:
            # First setup ever — nothing cached to build entities from.
            raise ConfigEntryNotReady(exception) from exception
        LOGGER.warning(
            "Vacuum unreachable at setup; continuing with cached device info: %s",
            exception,
        )
        info = CachedDeviceInfo.from_stored(cast("JsonObject", stored))
        offline = True
    else:
        stored_info = CachedDeviceInfo.to_stored(info)
        if entry.data.get(CONF_DEVICE_INFO) != stored_info:
            hass.config_entries.async_update_entry(
                entry, data={**entry.data, CONF_DEVICE_INFO: stored_info}
            )
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

    if offline:
        async_raise_cannot_connect(hass, entry)
        # Tolerant refresh: entities are created and marked unavailable by the
        # coordinator instead of holding the whole entry in SETUP_RETRY.
        await coordinator.async_refresh()
    else:
        await coordinator.async_config_entry_first_refresh()
    if map_coordinator is not None:
        # The map is best-effort and must never block entity creation.
        await map_coordinator.async_load_cached()
        await map_coordinator.async_refresh()

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
