"""Battery level sensor for xiaomi_vacuum."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import PERCENTAGE, EntityCategory

from ..entity import XiaomiVacuumEntity  # noqa: TID252


class XiaomiVacuumBatterySensor(XiaomiVacuumEntity, SensorEntity):
    """Battery level sensor for the vacuum."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self) -> str:
        """Return a stable unique id for this entity."""
        return f"{self.coordinator.config_entry.entry_id}_battery"

    @property
    def native_value(self) -> int | None:
        """Return battery level 0-100."""
        level = self.coordinator.data.get("battery_level")
        return int(level) if level is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, bool | str | None] | None:
        """Expose whether the battery is currently charging."""
        charging_state = self.coordinator.data.get("charging_state")
        if charging_state is None:
            return None
        slug = self.coordinator.spec.charging_state_slugs.get(charging_state)
        return {
            "charging": slug == "charging",
            "charging_state": slug,
        }
