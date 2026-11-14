"""Dust collection frequency select entity."""

from __future__ import annotations

from ..spec import Property  # noqa: TID252
from .base import _XiaomiVacuumSelect


class XiaomiVacuumDustCollectionFrequencySelect(_XiaomiVacuumSelect):
    """Select after how many jobs the dock empties the dust bin."""

    _attr_translation_key = "dust_collection_frequency"

    _property_name = Property.DUST_COLLECTION_FREQUENCY

    @property
    def _slug_to_value(self) -> dict[str, int]:
        return dict(self.coordinator.spec.dust_collection_frequencies)
