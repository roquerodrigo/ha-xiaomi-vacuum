"""Resume-after-charge switch."""

from __future__ import annotations

from ..spec import Property  # noqa: TID252
from .base import _XiaomiVacuumSwitch


class XiaomiVacuumResumeAfterChargeSwitch(_XiaomiVacuumSwitch):
    """Resumes an unfinished job once the robot has recharged."""

    _attr_translation_key = "resume_after_charge"

    _property_name = Property.RESUME_AFTER_CHARGE
