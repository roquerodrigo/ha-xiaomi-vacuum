"""Mop-wash stop button."""

from __future__ import annotations

from .action_base import _XiaomiVacuumActionButton


class XiaomiVacuumStopMopWashButton(_XiaomiVacuumActionButton):
    """Stop washing the mop pads."""

    _attr_translation_key = "stop_mop_wash"

    _action_name = "stop_mop_wash"
