"""Clean-times select entity."""

from __future__ import annotations

from ..spec import Property  # noqa: TID252
from .base import _XiaomiVacuumSelect


class XiaomiVacuumCleanTimesSelect(_XiaomiVacuumSelect):
    """Select how many times the vacuum repeats a cleaning task."""

    _attr_translation_key = "clean_times"

    _property_name = Property.CLEAN_TIMES

    @property
    def _slug_to_value(self) -> dict[str, int]:
        return dict(self.coordinator.spec.clean_times)
