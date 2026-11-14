"""Mop wash frequency select entity."""

from __future__ import annotations

from ..spec import Property  # noqa: TID252
from .base import _XiaomiVacuumSelect


class XiaomiVacuumMopWashFrequencySelect(_XiaomiVacuumSelect):
    """Select what triggers a mop wash mid-job: each room, an area or a time."""

    _attr_translation_key = "mop_wash_frequency"

    _property_name = Property.MOP_WASH_FREQUENCY

    @property
    def _slug_to_value(self) -> dict[str, int]:
        return dict(self.coordinator.spec.mop_wash_frequencies)
