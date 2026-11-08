"""A live fault published as a plain integer code."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .fault_reading import FaultReading

if TYPE_CHECKING:
    from ...data import VacuumState  # noqa: TID252


class PlainFaultReading(FaultReading):
    """A ``fault`` property holding one code, 0 when healthy (S20+, X20+)."""

    def live_code(
        self,
        data: VacuumState,
        ignored: frozenset[int],
        notices: frozenset[int],  # noqa: ARG002
    ) -> int | None:
        """Return the published code, or 0 when it is a phantom fault."""
        value = data.get("fault")
        if not isinstance(value, int):
            return None
        return 0 if value in ignored else int(value)
