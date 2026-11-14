"""Auto dust collection switch."""

from __future__ import annotations

from ..spec import Property  # noqa: TID252
from .base import _XiaomiVacuumSwitch


class XiaomiVacuumAutoDustCollectionSwitch(_XiaomiVacuumSwitch):
    """Empties the dust bin into the dock after each job."""

    _attr_translation_key = "auto_dust_collection"

    _property_name = Property.AUTO_DUST_COLLECTION
