"""Raw device fault-code sensor for xiaomi_vacuum."""

from __future__ import annotations

import json

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

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """
        Show all live fault IDs, including ones hidden from the headline code.

        The normal fault sensor exposes the highest-priority code only.  This
        diagnostic view retains the complete payload for investigation without
        mistaking unsupported-dock phantom faults for actionable conditions.
        Invalid/unavailable payloads remain unknown rather than healthy.
        """
        data = self.coordinator.data
        raw = data.get("fault_ids")
        if isinstance(raw, str):
            try:
                payload = json.loads(raw)
            except ValueError, TypeError:
                payload = None
            values = payload.get("fault") if isinstance(payload, dict) else None
            codes = (
                sorted({code for code in values if type(code) is int and code > 0})
                if isinstance(values, list)
                else None
            )
        else:
            code = data.get("fault")
            codes = (
                [code]
                if type(code) is int and code > 0
                else ([] if code == 0 else None)
            )
        spec = self.coordinator.spec
        actionable = (
            [code for code in codes if code not in spec.ignored_fault_codes]
            if codes is not None
            else None
        )
        return {
            "active_fault_codes": actionable,
            "raw_fault_codes": codes,
            "ignored_fault_codes": (
                [code for code in codes if code in spec.ignored_fault_codes]
                if codes is not None
                else None
            ),
            "fault_text": data.get("fault_text"),
            "cloud_fault_history": self.coordinator.fault_history,
        }
