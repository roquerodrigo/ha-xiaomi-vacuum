"""Mop-wash time interval number entity."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfTime

from ..entity import XiaomiVacuumEntity  # noqa: TID252
from ..spec import Property  # noqa: TID252


class XiaomiVacuumMopWashTimeIntervalNumber(XiaomiVacuumEntity, NumberEntity):
    """Minutes of mopping between two mop washes when washing by time."""

    _attr_translation_key = "mop_wash_time_interval"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0
    _attr_native_max_value = 255
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.BOX

    @property
    def unique_id(self) -> str:
        """Return a stable unique id for this entity."""
        return f"{self.coordinator.config_entry.entry_id}_mop_wash_time_interval"

    @property
    def native_value(self) -> int | None:
        """Return the current interval, or None when unknown."""
        value = self.coordinator.data.get(Property.MOP_WASH_TIME_INTERVAL)
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    async def async_set_native_value(self, value: float) -> None:
        """Set the interval, with optimistic update."""
        minutes = round(value)
        client = self.coordinator.config_entry.runtime_data.client
        await client.async_set_property(Property.MOP_WASH_TIME_INTERVAL, value=minutes)
        self._patch_state(mop_wash_time_interval=minutes)
        self._schedule_refresh()
