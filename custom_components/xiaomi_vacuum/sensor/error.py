"""Device fault sensor for xiaomi_vacuum."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory

from ..entity import XiaomiVacuumEntity  # noqa: TID252

if TYPE_CHECKING:
    from ..coordinator import XiaomiVacuumDataUpdateCoordinator  # noqa: TID252


class XiaomiVacuumErrorSensor(XiaomiVacuumEntity, SensorEntity):
    """
    Device fault sensor (live Fault Ids, siid 2 / piid 66).

    The device reports a numeric fault code. There is no static code->text
    table for this model anywhere in Xiaomi's ecosystem; the human-readable,
    already-localized text is delivered by the cloud as a device message and
    resolved by the coordinator into ``fault_text``. Shows ``OK`` when there is
    no fault, the localized text when available, or ``Error <code>`` otherwise.
    The raw code is always exposed as the ``fault_code`` attribute.
    """

    _attr_translation_key = "error"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: XiaomiVacuumDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_error"

    @property
    def native_value(self) -> str | None:
        """Return localized fault text, ``OK`` when healthy, or ``Error <code>``."""
        data = self.coordinator.data
        fault = data.get("fault")
        if fault is None:
            return None
        if int(fault) == 0:
            return "OK"
        return data.get("fault_text") or f"Error {int(fault)}"

    @property
    def extra_state_attributes(self) -> dict[str, int | None]:
        """Keep the raw numeric fault code available."""
        fault = self.coordinator.data.get("fault")
        return {"fault_code": int(fault) if fault is not None else None}
