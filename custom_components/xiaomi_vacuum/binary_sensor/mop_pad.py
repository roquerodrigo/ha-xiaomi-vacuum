"""Mop-pad-attached binary sensor for xiaomi_vacuum."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import EntityCategory

from ..entity import XiaomiVacuumEntity  # noqa: TID252


class XiaomiVacuumMopPadBinarySensor(XiaomiVacuumEntity, BinarySensorEntity):
    """
    Whether the mop pad is physically attached to the vacuum.

    The vacuum silently rejects sweep-mop-type writes when no mop pad is
    detected (acks code 0 but reverts on the next poll). Exposing this state as
    a binary sensor lets the user see *why* a mode change didn't stick, and the
    sweep-mop-type select uses it to raise a clear error instead of failing
    silently.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "mop_pad"

    @property
    def unique_id(self) -> str:
        """Return a stable unique id for this entity."""
        return f"{self.coordinator.config_entry.entry_id}_mop_pad"

    @property
    def is_on(self) -> bool | None:
        """Return True when the mop pad is attached, None when unknown."""
        value = self.coordinator.data.get("mop_status")
        if value is None:
            return None
        # Coerce to bool in case the device returns 0/1 instead of false/true.
        return bool(value)
