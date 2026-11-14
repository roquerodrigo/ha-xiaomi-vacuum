"""Carpet cleaning method select entity."""

from __future__ import annotations

from ..spec import Property  # noqa: TID252
from .base import _XiaomiVacuumSelect


class XiaomiVacuumCarpetCleaningMethodSelect(_XiaomiVacuumSelect):
    """Select how the robot treats carpets."""

    _attr_translation_key = "carpet_cleaning_method"

    _property_name = Property.CARPET_CLEANING_METHOD

    @property
    def _slug_to_value(self) -> dict[str, int]:
        return dict(self.coordinator.spec.carpet_cleaning_methods)
