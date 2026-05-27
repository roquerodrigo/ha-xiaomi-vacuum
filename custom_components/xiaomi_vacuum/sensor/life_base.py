"""Shared base for consumable remaining-life sensors."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory

from ..entity import XiaomiVacuumEntity  # noqa: TID252

if TYPE_CHECKING:
    from ..coordinator import XiaomiVacuumDataUpdateCoordinator  # noqa: TID252


class _XiaomiVacuumLifeSensor(XiaomiVacuumEntity, SensorEntity):
    """Remaining-life percentage of a consumable (MIoT life-level property)."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    _property_name: ClassVar[str]

    def __init__(self, coordinator: XiaomiVacuumDataUpdateCoordinator) -> None:
        """Initialize, deriving the unique_id from the translation key."""
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{self._attr_translation_key}"
        )

    @property
    def native_value(self) -> int | None:
        """Return the remaining life 0-100, or None when unknown."""
        value = self.coordinator.data.get(self._property_name)
        return int(cast("int", value)) if value is not None else None
