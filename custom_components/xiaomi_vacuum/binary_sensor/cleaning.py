"""Cleaning-in-progress binary sensor for xiaomi_vacuum."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.helpers.restore_state import RestoreEntity

from ..entity import XiaomiVacuumEntity  # noqa: TID252
from ..spec import CleaningJobSignal  # noqa: TID252


class XiaomiVacuumCleaningBinarySensor(
    XiaomiVacuumEntity, BinarySensorEntity, RestoreEntity
):
    """
    Whether a cleaning job is underway, from its start until the vacuum is done.

    Unlike the vacuum activity, it stays on through the pauses inside a job
    (mop washes, mid-job recharges, a user pause). Statuses the device reports
    both mid-job and after the job ends keep the previous verdict, which is
    restored across restarts so a job ending inside such a status is not lost.
    """

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_translation_key = "cleaning"
    _cleaning_in_progress: bool | None = None

    @property
    def unique_id(self) -> str:
        """Return a stable unique id for this entity."""
        return f"{self.coordinator.config_entry.entry_id}_cleaning"

    @property
    def is_on(self) -> bool | None:
        """Return True while a cleaning job is underway, None when unknown."""
        return self._cleaning_in_progress

    async def async_added_to_hass(self) -> None:
        """Restore the last verdict, then reconcile it with the current status."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in (STATE_ON, STATE_OFF):
            self._cleaning_in_progress = last_state.state == STATE_ON
        self._follow_status()

    def _handle_coordinator_update(self) -> None:
        """Update the verdict from the freshly polled status."""
        self._follow_status()
        super()._handle_coordinator_update()

    def _follow_status(self) -> None:
        status = self.coordinator.data.get("status")
        if status is None:
            return
        signal = self.coordinator.spec.cleaning_job_signals.get(int(status))
        if signal is CleaningJobSignal.IN_PROGRESS:
            self._cleaning_in_progress = True
        elif signal is CleaningJobSignal.FINISHED:
            self._cleaning_in_progress = False
