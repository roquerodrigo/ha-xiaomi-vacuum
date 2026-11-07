"""Child-lock switch."""

from __future__ import annotations

from ..spec import Property  # noqa: TID252
from .base import _XiaomiVacuumSwitch


class XiaomiVacuumChildLockSwitch(_XiaomiVacuumSwitch):
    """Locks the robot's physical buttons."""

    _attr_translation_key = "child_lock"

    _property_name = Property.CHILD_LOCK
