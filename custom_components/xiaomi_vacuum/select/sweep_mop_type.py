"""Sweep/mop type select entity."""

from __future__ import annotations

from typing import ClassVar

from ..const import SWEEP_MOP_TYPE_NAMES, SWEEP_MOP_TYPES  # noqa: TID252
from .base import _XiaomiVacuumSelect


class XiaomiVacuumSweepMopTypeSelect(_XiaomiVacuumSelect):
    """Select the sweep/mop type the vacuum uses while cleaning."""

    _attr_translation_key = "sweep_mop_type"
    _attr_icon = "mdi:broom"
    _attr_options: ClassVar[list[str]] = list(SWEEP_MOP_TYPES)

    _property_name = "sweep_mop_type"
    _slug_to_value: ClassVar[dict[str, int]] = SWEEP_MOP_TYPES
    _value_to_slug: ClassVar[dict[int, str]] = SWEEP_MOP_TYPE_NAMES
