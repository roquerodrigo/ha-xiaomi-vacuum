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

    @staticmethod
    def primary_code(
        codes: list[int] | None,
        ignored: frozenset[int],
        notices: frozenset[int],
    ) -> int | None:
        """
        Return the primary code: 0 when healthy, None when not reported.

        Codes in ``ignored`` are the model's phantom faults and never count; a
        real fault wins over a code in ``notices`` when both are published.
        """
        if codes is None:
            return None
        active = [code for code in codes if code not in ignored]
        active.sort(key=lambda code: code in notices)
        return active[0] if active else 0

    def live_code(
        self,
        data: VacuumState,
        ignored: frozenset[int],
        notices: frozenset[int],
    ) -> int | None:
        """Return the primary code of a polled state."""
        return self.primary_code(self.raw_codes(data), ignored, notices)
