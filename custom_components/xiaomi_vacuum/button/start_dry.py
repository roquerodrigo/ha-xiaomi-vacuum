"""Mop-drying start button."""

from __future__ import annotations

from .action_base import _XiaomiVacuumActionButton


class XiaomiVacuumStartDryButton(_XiaomiVacuumActionButton):
    """Start drying the mop pads in the dock."""

    _attr_translation_key = "start_dry"

    _action_name = "start_dry"
