"""Real device-status sensor for xiaomi_vacuum."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity

from ..const import STATUS_SLUGS  # noqa: TID252
from ..entity import XiaomiVacuumEntity  # noqa: TID252

if TYPE_CHECKING:
    from ..coordinator import XiaomiVacuumDataUpdateCoordinator  # noqa: TID252

# Static option list for the ENUM sensor; module-level so it isn't rebuilt per
# access and doesn't trip RUF012 (HA types `_attr_options` as an instance var).
_STATUS_OPTIONS = list(STATUS_SLUGS.values())


class XiaomiVacuumStatusSensor(XiaomiVacuumEntity, SensorEntity):
    """The vacuum's raw device status (more granular than the HA activity)."""

    _attr_translation_key = "status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = _STATUS_OPTIONS

    def __init__(self, coordinator: XiaomiVacuumDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_status"

    @property
    def native_value(self) -> str | None:
        """Return the current device status as a slug, or None when unknown."""
        status = self.coordinator.data.get("status")
        return STATUS_SLUGS.get(int(status)) if status is not None else None
