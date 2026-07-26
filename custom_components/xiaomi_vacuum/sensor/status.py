"""Real device-status sensor for xiaomi_vacuum."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity

from ..entity import XiaomiVacuumEntity  # noqa: TID252


class XiaomiVacuumStatusSensor(XiaomiVacuumEntity, SensorEntity):
    """
    The vacuum's raw device status (more granular than the HA activity).

    The status-code set and slugs differ per model (the S20+ has 10 codes, the
    X20 Max has 21), so both the option list and the lookup come from the active
    model's spec.
    """

    _attr_translation_key = "status"
    _attr_device_class = SensorDeviceClass.ENUM

    @property
    def unique_id(self) -> str:
        """Return a stable unique id for this entity."""
        return f"{self.coordinator.config_entry.entry_id}_status"

    @property
    def options(self) -> list[str]:
        """Status slugs advertised by this model's spec (ENUM sensor option set)."""
        return list(self.coordinator.spec.status_slugs.values())

    @property
    def native_value(self) -> str | None:
        """Return the current device status as a slug, or None when unknown."""
        status = self.coordinator.data.get("status")
        if status is None:
            return None
        return self.coordinator.spec.status_slugs.get(int(status))
