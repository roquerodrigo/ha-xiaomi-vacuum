"""XiaomiVacuumEntity base class."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME, DOMAIN
from .coordinator import XiaomiVacuumDataUpdateCoordinator
from .spec import DEFAULT_MODEL

if TYPE_CHECKING:
    from .data import VacuumState


class XiaomiVacuumEntity(CoordinatorEntity[XiaomiVacuumDataUpdateCoordinator]):
    """Base entity for Xiaomi Vacuum."""

    _attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Describe the vacuum device this entity belongs to."""
        entry = self.coordinator.config_entry
        info = entry.runtime_data.info
        model = getattr(info, "model", None) or DEFAULT_MODEL
        name = entry.data.get(CONF_NAME) or model
        mac = getattr(info, "mac_address", None)
        connections = {(CONNECTION_NETWORK_MAC, mac)} if mac else set()
        return DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            connections=connections,
            name=name,
            manufacturer="Xiaomi",
            model=model,
            sw_version=getattr(info, "firmware_version", None),
            hw_version=getattr(info, "hardware_version", None),
        )

    def _patch_state(self, **patch: int | str | None) -> None:
        """Optimistic state patch so the UI reflects a command instantly."""
        data = dict(self.coordinator.data)
        data.update(patch)
        self.coordinator.async_set_updated_data(cast("VacuumState", data))

    def _schedule_refresh(self, delay: float = 5.0) -> None:
        """Background refresh after delay; device takes ~1-2s to reflect commands."""

        async def _later() -> None:
            await asyncio.sleep(delay)
            await self.coordinator.async_refresh()

        self.hass.async_create_background_task(
            _later(), f"{DOMAIN}_post_command_refresh"
        )
