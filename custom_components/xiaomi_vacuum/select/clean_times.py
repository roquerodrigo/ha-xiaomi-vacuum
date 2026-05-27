"""Clean-times select entity."""

from __future__ import annotations

from typing import ClassVar

from ..const import CLEAN_TIMES, CLEAN_TIMES_NAMES  # noqa: TID252
from .base import _XiaomiVacuumSelect


class XiaomiVacuumCleanTimesSelect(_XiaomiVacuumSelect):
    """Select how many times the vacuum passes over each area."""

    _attr_translation_key = "clean_times"
    _attr_icon = "mdi:repeat"

    _property_name = "clean_times"
    _slug_to_value: ClassVar[dict[str, int]] = CLEAN_TIMES
    _value_to_slug: ClassVar[dict[int, str]] = CLEAN_TIMES_NAMES
