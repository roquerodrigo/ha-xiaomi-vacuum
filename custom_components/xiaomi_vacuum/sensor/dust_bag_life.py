"""Dust-bag remaining-life sensor."""

from __future__ import annotations

from .life_base import _XiaomiVacuumLifeSensor


class XiaomiVacuumDustBagLifeSensor(_XiaomiVacuumLifeSensor):
    """Remaining life of the dust bag."""

    _attr_translation_key = "dust_bag_life"
    _attr_icon = "mdi:trash-can-outline"

    _property_name = "dust_bag_life"
