"""Raw device fault-code sensor for xiaomi_vacuum."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory

from ..entity import XiaomiVacuumEntity  # noqa: TID252

if TYPE_CHECKING:
    from ..coordinator import XiaomiVacuumDataUpdateCoordinator  # noqa: TID252


class XiaomiVacuumErrorCodeSensor(XiaomiVacuumEntity, SensorEntity):
    """Raw fault code from live Fault Ids (siid 2 / piid 66); 0 means no error."""

    _attr_translation_key = "error_code"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: XiaomiVacuumDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_error_code"

    @property
    def native_value(self) -> int | None:
        """Return the numeric fault code (0 = no error)."""
        fault = self.coordinator.data.get("fault")
        return int(fault) if fault is not None else None
