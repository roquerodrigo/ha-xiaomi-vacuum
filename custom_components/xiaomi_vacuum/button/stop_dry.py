"""Mop-drying stop button."""

from __future__ import annotations

from .action_base import _XiaomiVacuumActionButton


class XiaomiVacuumStopDryButton(_XiaomiVacuumActionButton):
    """Stop drying the mop pads."""

    _attr_translation_key = "stop_dry"

    _action_name = "stop_dry"
