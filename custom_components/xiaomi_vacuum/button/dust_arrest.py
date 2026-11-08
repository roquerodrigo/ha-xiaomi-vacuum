"""Dust-arrest button entity for xiaomi_vacuum."""

from __future__ import annotations

from .action_base import _XiaomiVacuumActionButton


class XiaomiVacuumDustArrestButton(_XiaomiVacuumActionButton):
    """Triggers the dock to empty the vacuum's dust bin."""

    _attr_translation_key = "dust_arrest"
    _action_name = "start_dust_arrest"
