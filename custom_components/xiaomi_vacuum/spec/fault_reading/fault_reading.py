"""How a model publishes its live fault."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...data import VacuumState  # noqa: TID252


class FaultReading(ABC):
    """Decodes the polled fault property and selects the primary code."""

    @abstractmethod
    def raw_codes(self, data: VacuumState) -> list[int] | None:
        """Return reported positive codes, or None when unknown."""

    def live_code(
        self,
        data: VacuumState,
        ignored: frozenset[int],
        notices: frozenset[int],
    ) -> int | None:
        """Return the primary code, prioritizing faults over notices."""
        codes = (
            data["raw_fault_codes"]
            if "raw_fault_codes" in data
            else self.raw_codes(data)
        )
        if codes is None:
            return None
        active = [code for code in codes if code not in ignored]
        active.sort(key=lambda code: code in notices)
        return active[0] if active else 0
