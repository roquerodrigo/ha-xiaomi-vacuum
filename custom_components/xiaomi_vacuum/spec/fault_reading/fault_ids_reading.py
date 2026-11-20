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

    def raw_codes(self, data: VacuumState) -> list[int] | None:
        """Decode the reported list, preserving device order."""
        raw = data.get("fault_ids")
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except ValueError, TypeError:
            return None
        if not isinstance(payload, dict):
            return None
        ids = payload.get("fault")
        if not isinstance(ids, list):
            return None
        if any(type(code) is not int or code < 0 for code in ids):
            return None
        return [code for code in ids if code > 0]
