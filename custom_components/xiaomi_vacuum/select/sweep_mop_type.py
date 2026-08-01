"""Sweep/mop type select entity."""

from __future__ import annotations

from homeassistant.exceptions import ServiceValidationError

from .base import _XiaomiVacuumSelect

#: Modes that require a mop pad to be physically attached. "sweep" does not.
_MOP_REQUIRED_MODES = frozenset({"mop", "sweep_mop", "sweep_before_mopping"})


class XiaomiVacuumSweepMopTypeSelect(_XiaomiVacuumSelect):
    """
    Select the sweep/mop type the vacuum uses while cleaning.

    The vacuum silently rejects mode changes to mop / sweep-mop / sweep-before-
    mopping when no mop pad is detected: it acks the write (code 0) but reverts
    on the next poll, surfacing in HA as the select mysteriously resetting to
    "sweep". Checking the mop-pad state before sending lets us raise a clear
    error instead.
    """

    _attr_translation_key = "sweep_mop_type"
    _attr_icon = "mdi:broom"

    _property_name = "sweep_mop_type"

    @property
    def _slug_to_value(self) -> dict[str, int]:
        return dict(self.coordinator.spec.sweep_mop_types)

    async def async_select_option(self, option: str) -> None:
        """Set the mode, refusing mop modes when the mop pad is not attached."""
        if option in _MOP_REQUIRED_MODES:
            mop_status = self.coordinator.data.get("mop_status")
            if mop_status is False:
                msg = (
                    "Cannot select a mop mode: no mop pad detected. Attach the "
                    "mop pad to the vacuum and try again."
                )
                raise ServiceValidationError(msg)
        await super().async_select_option(option)
