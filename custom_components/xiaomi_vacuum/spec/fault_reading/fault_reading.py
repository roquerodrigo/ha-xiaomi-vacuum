"""How a model publishes its live fault."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...data import VacuumState  # noqa: TID252


class FaultReading(ABC):
    """Turns the polled fault property into the one live fault code."""

    @abstractmethod
    def live_code(
        self,
        data: VacuumState,
        ignored: frozenset[int],
        notices: frozenset[int],
    ) -> int | None:
        """
        Return the live fault code: 0 when healthy, None when not reported.

        Codes in ``ignored`` are the model's phantom faults and never count; a
        real fault wins over a code in ``notices`` when both are published.
        """
