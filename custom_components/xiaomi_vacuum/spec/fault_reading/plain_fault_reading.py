"""A live fault published as a plain integer code."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .fault_reading import FaultReading

if TYPE_CHECKING:
    from ...data import VacuumState  # noqa: TID252


class PlainFaultReading(FaultReading):
    """A ``fault`` property holding one code, 0 when healthy (S20+, X20+)."""

    def raw_codes(self, data: VacuumState) -> list[int] | None:
        """Return the numeric code before model-specific filtering."""
        value = data.get("fault")
        if type(value) is not int or value < 0:
            return None
        return [value] if value else []
