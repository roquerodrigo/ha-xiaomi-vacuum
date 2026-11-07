"""Mop-wash start button."""

from __future__ import annotations

from .action_base import _XiaomiVacuumActionButton


class XiaomiVacuumStartMopWashButton(_XiaomiVacuumActionButton):
    """Start washing the mop pads in the dock."""

    _attr_translation_key = "start_mop_wash"

    _action_name = "start_mop_wash"
