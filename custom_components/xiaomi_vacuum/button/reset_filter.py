"""Filter life reset button."""

from __future__ import annotations

from homeassistant.const import EntityCategory

from .action_base import _XiaomiVacuumActionButton


class XiaomiVacuumResetFilterButton(_XiaomiVacuumActionButton):
    """Reset the filter life after replacing it."""

    _attr_translation_key = "reset_filter"
    _attr_entity_category = EntityCategory.CONFIG
    _action_name = "reset_filter"
