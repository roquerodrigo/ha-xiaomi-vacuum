"""Side-brush life reset button."""

from __future__ import annotations

from homeassistant.const import EntityCategory

from .action_base import _XiaomiVacuumActionButton


class XiaomiVacuumResetSideBrushButton(_XiaomiVacuumActionButton):
    """Reset the side-brush life after replacing it."""

    _attr_translation_key = "reset_side_brush"
    _attr_entity_category = EntityCategory.CONFIG
    _action_name = "reset_side_brush"
