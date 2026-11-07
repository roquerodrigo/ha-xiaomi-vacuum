"""Shared base for sensors that show one integer MIoT property as is."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from homeassistant.components.sensor import SensorEntity

from ..entity import XiaomiVacuumEntity  # noqa: TID252

if TYPE_CHECKING:
    from ..spec import Property  # noqa: TID252


class _XiaomiVacuumPropertySensor(XiaomiVacuumEntity, SensorEntity):
    """An integer property read straight from the polled state."""

    _property_name: ClassVar[Property]

    @property
    def unique_id(self) -> str:
        """Return a stable unique id derived from the translation key."""
        return f"{self.coordinator.config_entry.entry_id}_{self._attr_translation_key}"

    @property
    def native_value(self) -> int | None:
        """Return the property value, or None when unknown."""
        value = self.coordinator.data.get(self._property_name)
        return value if isinstance(value, int) and not isinstance(value, bool) else None
