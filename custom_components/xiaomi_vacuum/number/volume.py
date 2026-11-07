"""Voice volume number entity."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE, EntityCategory

from ..entity import XiaomiVacuumEntity  # noqa: TID252
from ..spec import Property  # noqa: TID252


class XiaomiVacuumVolumeNumber(XiaomiVacuumEntity, NumberEntity):
    """Volume of the robot's voice prompts, 0-100."""

    _attr_translation_key = "volume"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER

    @property
    def unique_id(self) -> str:
        """Return a stable unique id for this entity."""
        return f"{self.coordinator.config_entry.entry_id}_volume"

    @property
    def native_value(self) -> int | None:
        """Return the current volume, or None when unknown."""
        value = self.coordinator.data.get(Property.VOLUME)
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    async def async_set_native_value(self, value: float) -> None:
        """Set the volume, with optimistic update."""
        volume = round(value)
        client = self.coordinator.config_entry.runtime_data.client
        await client.async_set_property(Property.VOLUME, value=volume)
        self._patch_state(volume=volume)
        self._schedule_refresh()
