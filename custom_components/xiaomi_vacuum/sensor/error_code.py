"""Raw device fault-code sensor for xiaomi_vacuum."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory

from ..entity import XiaomiVacuumEntity  # noqa: TID252


class XiaomiVacuumErrorCodeSensor(XiaomiVacuumEntity, SensorEntity):
    """Raw fault code from live Fault Ids (siid 2 / piid 66); 0 means no error."""

    _attr_translation_key = "error_code"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self) -> str:
        """Return a stable unique id for this entity."""
        return f"{self.coordinator.config_entry.entry_id}_error_code"

    @property
    def native_value(self) -> int | None:
        """Return the numeric fault code (0 = no error)."""
        fault = self.coordinator.data.get("fault")
        return int(fault) if fault is not None else None
