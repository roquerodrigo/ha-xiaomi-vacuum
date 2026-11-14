"""Auto mop drying switch."""

from __future__ import annotations

from ..spec import Property  # noqa: TID252
from .base import _XiaomiVacuumSwitch


class XiaomiVacuumAutoMopDryingSwitch(_XiaomiVacuumSwitch):
    """Dries the mop pads at the dock after each job."""

    _attr_translation_key = "auto_mop_drying"

    _property_name = Property.AUTO_MOP_DRYING
