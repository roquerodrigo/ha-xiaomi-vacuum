"""Battery level sensor for xiaomi_vacuum."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import PERCENTAGE, EntityCategory

from ..entity import XiaomiVacuumEntity  # noqa: TID252

if TYPE_CHECKING:
    from ..coordinator import XiaomiVacuumDataUpdateCoordinator  # noqa: TID252


class XiaomiVacuumBatterySensor(XiaomiVacuumEntity, SensorEntity):
    """Battery level sensor for the vacuum."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: XiaomiVacuumDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_battery"

    @property
    def native_value(self) -> int | None:
        """Return battery level 0-100."""
        level = self.coordinator.data.get("battery_level")
        return int(level) if level is not None else None
