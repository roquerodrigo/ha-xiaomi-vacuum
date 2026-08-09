"""Xiaomi Vacuum integration for Home Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.loader import async_get_loaded_integration

from .api import XiaomiVacuumApiClient, XiaomiVacuumApiClientCommunicationError
from .cached_device_info import CachedDeviceInfo
from .cloud import XiaomiCloud, XiaomiCloudConnectionError, XiaomiCloudError
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
from .repairs import (
    async_clear_cannot_connect,
    async_clear_unsupported_model,
    async_raise_cannot_connect,
    async_raise_unsupported_model,
)
from .spec import DEFAULT_MODEL, SUPPORTED_MODELS, get_spec

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import DeviceInfoLike, JsonObject, XiaomiVacuumConfigEntry

PLATFORMS: list[Platform] = [
    Platform.VACUUM,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.IMAGE,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]


async def _setup_cloud(
    hass: HomeAssistant,
    entry: XiaomiVacuumConfigEntry,
    coordinator: XiaomiVacuumDataUpdateCoordinator,
    client: XiaomiVacuumApiClient,
) -> XiaomiVacuumMapCoordinator | None:
    """
    Resolve the cloud session, wire it into the client + coordinator.

    Returns the map coordinator (None when no session, or when the session is
    invalid and reauth has been triggered). Raises ConfigEntryNotReady when the
    cloud is unreachable so Home Assistant retries the whole entry. The cloud
    also backs cloud-routed actions (e.g. the S20+ room-clean) via
    ``client.set_cloud``.
    """
    cloud_country = entry.data.get(CONF_CLOUD_COUNTRY)
    ssecurity = entry.data.get(CONF_CLOUD_SSECURITY)
    service_token = entry.data.get(CONF_CLOUD_SERVICE_TOKEN)
    cloud_user_id = entry.data.get(CONF_CLOUD_USER_ID)
    if not (cloud_country and ssecurity and service_token and cloud_user_id):
        return None
    cloud = XiaomiCloud.from_session(
        hass,
        country=cloud_country,
        ssecurity=ssecurity,
        service_token=service_token,
        user_id=cloud_user_id,
    )
    try:
        await cloud.async_resolve_device(entry.data[CONF_TOKEN])
    except XiaomiCloudConnectionError as exception:
        # Transient network failure (e.g. DNS not up yet while the host boots):
        # retry the whole entry instead of treating it as an expired session.
        raise ConfigEntryNotReady(exception) from exception
    except XiaomiCloudError as exception:
        LOGGER.warning(
            "Cloud session invalid; starting reauth to refresh: %s", exception
        )
        # Surface a repair/reauth prompt instead of silently dropping the map;
        # local entities stay available since the entry itself keeps loading.
        entry.async_start_reauth(hass)
        return None
    coordinator.cloud = cloud
    # Route multi-step actions (e.g. the S20+ room-clean) through the cloud for
    # reliability — local UDP routinely times out (-9999).
    client.set_cloud(cloud)
    return XiaomiVacuumMapCoordinator(hass, cloud=cloud, state_coordinator=coordinator)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: XiaomiVacuumConfigEntry,
) -> bool:
    """Set up Xiaomi Vacuum from a config entry."""
    coordinator = XiaomiVacuumDataUpdateCoordinator(hass=hass, config_entry=entry)
    # Model is unknown until the local handshake succeeds; provisionally pick
    # the cached/default model so the client can be built. Once the handshake
    # resolves a different model we rebuild the client with the right spec.
    stored_info = entry.data.get(CONF_DEVICE_INFO)
    cached_model = stored_info.get("model") if isinstance(stored_info, dict) else None
    provisional_spec = get_spec(cached_model or DEFAULT_MODEL)
    client = XiaomiVacuumApiClient(
        host=entry.data[CONF_HOST],
        token=entry.data[CONF_TOKEN],
        spec=provisional_spec,
    )
    offline = False
    info: DeviceInfoLike
    try:
        info = await client.async_get_info()
    except XiaomiVacuumApiClientCommunicationError as exception:
        if not stored_info:
            # First setup ever — nothing cached to build entities from.
            raise ConfigEntryNotReady(exception) from exception
        LOGGER.warning(
            "Vacuum unreachable at setup; continuing with cached device info: %s",
            exception,
        )
        info = CachedDeviceInfo.from_stored(cast("JsonObject", stored_info))
        offline = True
    else:
        stored_info_obj = CachedDeviceInfo.to_stored(info)
        if entry.data.get(CONF_DEVICE_INFO) != stored_info_obj:
            hass.config_entries.async_update_entry(
                entry, data={**entry.data, CONF_DEVICE_INFO: stored_info_obj}
            )
    LOGGER.debug(
        "Device info: model=%s raw=%s",
        getattr(info, "model", None),
        getattr(info, "raw", None),
    )
    # Resolve the real spec from the (now-known) model and rebuild the client if
    # the handshake revealed a different model than the cached/default one.
    model = getattr(info, "model", None)
    spec = get_spec(model)
    if model and model not in SUPPORTED_MODELS:
        async_raise_unsupported_model(hass, entry, model)
    else:
        async_clear_unsupported_model(hass, entry)
    if spec is not provisional_spec:
        client = XiaomiVacuumApiClient(
            host=entry.data[CONF_HOST],
            token=entry.data[CONF_TOKEN],
            spec=spec,
        )
    map_coordinator = await _setup_cloud(hass, entry, coordinator, client)

    entry.runtime_data = XiaomiVacuumData(
        client=client,
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
        info=info,
        spec=spec,
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

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: XiaomiVacuumConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(
    hass: HomeAssistant,
    entry: XiaomiVacuumConfigEntry,
) -> None:
    """Delete the per-entry repair issues when the entry itself is deleted."""
    async_clear_cannot_connect(hass, entry)
    async_clear_unsupported_model(hass, entry)
