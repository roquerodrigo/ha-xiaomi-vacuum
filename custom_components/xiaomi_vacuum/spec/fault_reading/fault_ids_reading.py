"""A live fault published as a JSON list of fault ids."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .fault_reading import FaultReading

if TYPE_CHECKING:
    from ...data import VacuumState  # noqa: TID252


class FaultIdsReading(FaultReading):
    """
    The X20 Max ``Fault Ids`` property: ``{"ts": ..., "fault": [<codes>]}``.

    A healthy robot publishes either ``[0]`` or an empty list; both are observed
    on real hardware, so both count as no active fault. The ``Device Fault``
    property next to it is not used: it latches the last code and never resets.
    """

    def live_code(
        self,
        data: VacuumState,
        ignored: frozenset[int],
        notices: frozenset[int],
    ) -> int | None:
        """Return the first active code of the list, real faults first."""
        fault_ids_raw = data.get("fault_ids")
        if not fault_ids_raw:
            return None
        try:
            ids = json.loads(fault_ids_raw).get("fault") or []
        except ValueError, TypeError, AttributeError:
            return None
        active = [code for code in ids if code and code not in ignored]
        active.sort(key=lambda code: code in notices)
        return active[0] if active else 0
