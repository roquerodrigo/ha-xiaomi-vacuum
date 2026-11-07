"""Do-not-disturb switch."""

from __future__ import annotations

from ..spec import Property  # noqa: TID252
from .base import _XiaomiVacuumSwitch


class XiaomiVacuumDoNotDisturbSwitch(_XiaomiVacuumSwitch):
    """Keeps the robot quiet during the quiet hours set in Mi Home."""

    _attr_translation_key = "do_not_disturb"

    _property_name = Property.DO_NOT_DISTURB
    _boolean = True
