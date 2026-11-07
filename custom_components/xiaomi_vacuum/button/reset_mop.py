"""Mop-pad life reset button."""

from __future__ import annotations

from homeassistant.const import EntityCategory

from .action_base import _XiaomiVacuumActionButton


class XiaomiVacuumResetMopButton(_XiaomiVacuumActionButton):
    """Reset the mop-pad life after replacing them."""

    _attr_translation_key = "reset_mop"
    _attr_entity_category = EntityCategory.CONFIG
    _action_name = "reset_mop"
