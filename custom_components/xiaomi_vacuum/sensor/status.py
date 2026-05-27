"""Real device-status sensor for xiaomi_vacuum."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity

from ..const import STATUS_SLUGS  # noqa: TID252
from ..entity import XiaomiVacuumEntity  # noqa: TID252

if TYPE_CHECKING:
    from ..coordinator import XiaomiVacuumDataUpdateCoordinator  # noqa: TID252


class XiaomiVacuumStatusSensor(XiaomiVacuumEntity, SensorEntity):
    """The vacuum's raw device status (more granular than the HA activity)."""

    _attr_translation_key = "status"
    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(self, coordinator: XiaomiVacuumDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_status"

    @property
    def options(self) -> list[str]:
        """Return every possible status slug (see STATUS_SLUGS)."""
        return list(STATUS_SLUGS.values())

    @property
    def native_value(self) -> str | None:
        """Return the current device status as a slug, or None when unknown."""
        status = self.coordinator.data.get("status")
        return STATUS_SLUGS.get(int(status)) if status is not None else None
