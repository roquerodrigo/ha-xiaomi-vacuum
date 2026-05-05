"""XiaomiVacuumEntity base class."""

from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, CONF_NAME, DOMAIN, MODEL
from .coordinator import XiaomiVacuumDataUpdateCoordinator


class XiaomiVacuumEntity(CoordinatorEntity[XiaomiVacuumDataUpdateCoordinator]):
    """Base entity for Xiaomi Vacuum."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(self, coordinator: XiaomiVacuumDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        info = entry.runtime_data.info
        model = getattr(info, "model", None) or MODEL
        name = entry.data.get(CONF_NAME) or model
        mac = getattr(info, "mac_address", None)
        connections = {(CONNECTION_NETWORK_MAC, mac)} if mac else set()
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            connections=connections,
            name=name,
            manufacturer="Xiaomi",
            model=model,
            sw_version=getattr(info, "firmware_version", None),
            hw_version=getattr(info, "hardware_version", None),
        )

    def _patch_state(self, **patch: Any) -> None:
        """Optimistic state patch so the UI reflects a command instantly."""
        data = dict(self.coordinator.data or {})
        data.update(patch)
        self.coordinator.async_set_updated_data(data)

    def _schedule_refresh(self, delay: float = 5.0) -> None:
        """Background refresh after delay; device takes ~1-2s to reflect commands."""

        async def _later() -> None:
            await asyncio.sleep(delay)
            await self.coordinator.async_refresh()

        self.hass.async_create_background_task(
            _later(), f"{DOMAIN}_post_command_refresh"
        )
