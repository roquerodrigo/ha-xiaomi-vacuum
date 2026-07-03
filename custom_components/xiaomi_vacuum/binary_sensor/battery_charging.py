"""Battery-charging binary sensor for xiaomi_vacuum."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory

from ..entity import XiaomiVacuumEntity  # noqa: TID252


class XiaomiVacuumBatteryChargingSensor(XiaomiVacuumEntity, BinarySensorEntity):
    """Whether the vacuum battery is currently charging."""

    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self) -> str:
        """Return a stable unique id for this entity."""
        return f"{self.coordinator.config_entry.entry_id}_battery_charging"

    @property
    def is_on(self) -> bool | None:
        """Return True while charging, None when the state is unknown."""
        charging_state = self.coordinator.data.get("charging_state")
        return charging_state == 1 if charging_state is not None else None
