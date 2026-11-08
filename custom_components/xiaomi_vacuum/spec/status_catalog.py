"""
The meaning of every status slug, shared by every model.

A slug means the same on every vacuum, so a model only maps its codes to slugs.
The ERROR activity never appears here: an active fault drives it (see
``XiaomiVacuum.activity``), and the bare ``error`` status shows up with no fault
during normal cycles. A status the device reports both mid-job and after it
(``station_working``, ``go_wash``) is ``INCONCLUSIVE`` and keeps the previous
cleaning-job verdict.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING

from homeassistant.components.vacuum.const import VacuumActivity

from .cleaning_job_signal import CleaningJobSignal
from .status_meaning import StatusMeaning
from .status_slug import StatusSlug

if TYPE_CHECKING:
    from collections.abc import Mapping

STATUS_MEANINGS: Mapping[StatusSlug, StatusMeaning] = MappingProxyType(
    {
        StatusSlug.BREAK_CHARGING: StatusMeaning(
            activity=VacuumActivity.DOCKED,
            is_idle=False,
            cleaning_job=CleaningJobSignal.IN_PROGRESS,
        ),
        StatusSlug.BUILDING_MAP: StatusMeaning(
            activity=VacuumActivity.CLEANING,
            is_idle=False,
            cleaning_job=CleaningJobSignal.IN_PROGRESS,
        ),
        StatusSlug.CHARGED: StatusMeaning(
            activity=VacuumActivity.DOCKED,
            is_idle=True,
            cleaning_job=CleaningJobSignal.FINISHED,
        ),
        StatusSlug.CHARGING: StatusMeaning(
            activity=VacuumActivity.DOCKED,
            is_idle=True,
            cleaning_job=CleaningJobSignal.FINISHED,
        ),
        StatusSlug.DRYING: StatusMeaning(
            activity=VacuumActivity.DOCKED,
            is_idle=True,
            cleaning_job=CleaningJobSignal.FINISHED,
        ),
        StatusSlug.DUST_COLLECTING: StatusMeaning(
            activity=VacuumActivity.DOCKED,
            is_idle=False,
            cleaning_job=CleaningJobSignal.INCONCLUSIVE,
        ),
        StatusSlug.ERROR: StatusMeaning(
            activity=VacuumActivity.IDLE,
            is_idle=False,
            cleaning_job=CleaningJobSignal.INCONCLUSIVE,
        ),
        StatusSlug.GO_CHARGE_BREAK: StatusMeaning(
            activity=VacuumActivity.RETURNING,
            is_idle=False,
            cleaning_job=CleaningJobSignal.IN_PROGRESS,
        ),
        StatusSlug.GO_CHARGE_BUILDING_MAP: StatusMeaning(
            activity=VacuumActivity.RETURNING,
            is_idle=False,
            cleaning_job=CleaningJobSignal.FINISHED,
        ),
        StatusSlug.GO_CHARGE_IN_STATION_ASSISTING_CLEANING: StatusMeaning(
            activity=VacuumActivity.RETURNING,
            is_idle=False,
            cleaning_job=CleaningJobSignal.INCONCLUSIVE,
        ),
        StatusSlug.GO_CHARGING: StatusMeaning(
            activity=VacuumActivity.RETURNING,
            is_idle=False,
            cleaning_job=CleaningJobSignal.FINISHED,
        ),
        StatusSlug.GO_WASH: StatusMeaning(
            activity=VacuumActivity.DOCKED,
            is_idle=False,
            cleaning_job=CleaningJobSignal.INCONCLUSIVE,
        ),
        StatusSlug.IDLE: StatusMeaning(
            activity=VacuumActivity.IDLE,
            is_idle=True,
            cleaning_job=CleaningJobSignal.FINISHED,
        ),
        StatusSlug.MAPPING_PAUSE: StatusMeaning(
            activity=VacuumActivity.PAUSED,
            is_idle=False,
            cleaning_job=CleaningJobSignal.IN_PROGRESS,
        ),
        StatusSlug.MOPPING: StatusMeaning(
            activity=VacuumActivity.CLEANING,
            is_idle=False,
            cleaning_job=CleaningJobSignal.IN_PROGRESS,
        ),
        StatusSlug.MULTI_TASK_RECHARGE: StatusMeaning(
            activity=VacuumActivity.RETURNING,
            is_idle=False,
            cleaning_job=CleaningJobSignal.IN_PROGRESS,
        ),
        StatusSlug.MULTI_TASK_STATION_WORKING: StatusMeaning(
            activity=VacuumActivity.DOCKED,
            is_idle=False,
            cleaning_job=CleaningJobSignal.IN_PROGRESS,
        ),
        StatusSlug.PAUSED: StatusMeaning(
            activity=VacuumActivity.PAUSED,
            is_idle=False,
            cleaning_job=CleaningJobSignal.IN_PROGRESS,
        ),
        StatusSlug.REMOTE: StatusMeaning(
            activity=VacuumActivity.CLEANING,
            is_idle=False,
            cleaning_job=CleaningJobSignal.IN_PROGRESS,
        ),
        StatusSlug.STATION_ASSISTING_CLEANED: StatusMeaning(
            activity=VacuumActivity.DOCKED,
            is_idle=False,
            cleaning_job=CleaningJobSignal.INCONCLUSIVE,
        ),
        StatusSlug.STATION_ASSISTING_CLEANING: StatusMeaning(
            activity=VacuumActivity.DOCKED,
            is_idle=False,
            cleaning_job=CleaningJobSignal.INCONCLUSIVE,
        ),
        StatusSlug.STATION_WORKING: StatusMeaning(
            activity=VacuumActivity.DOCKED,
            is_idle=False,
            cleaning_job=CleaningJobSignal.INCONCLUSIVE,
        ),
        StatusSlug.SWEEPING: StatusMeaning(
            activity=VacuumActivity.CLEANING,
            is_idle=False,
            cleaning_job=CleaningJobSignal.IN_PROGRESS,
        ),
        StatusSlug.SWEEPING_AND_MOPPING: StatusMeaning(
            activity=VacuumActivity.CLEANING,
            is_idle=False,
            cleaning_job=CleaningJobSignal.IN_PROGRESS,
        ),
        StatusSlug.UPDATING: StatusMeaning(
            activity=VacuumActivity.IDLE,
            is_idle=False,
            cleaning_job=CleaningJobSignal.FINISHED,
        ),
        StatusSlug.WASH_BREAK: StatusMeaning(
            activity=VacuumActivity.RETURNING,
            is_idle=False,
            cleaning_job=CleaningJobSignal.IN_PROGRESS,
        ),
        StatusSlug.WASHING_PAUSED: StatusMeaning(
            activity=VacuumActivity.PAUSED,
            is_idle=False,
            cleaning_job=CleaningJobSignal.IN_PROGRESS,
        ),
        StatusSlug.WATER_INSPECTING: StatusMeaning(
            activity=VacuumActivity.DOCKED,
            is_idle=False,
            cleaning_job=CleaningJobSignal.INCONCLUSIVE,
        ),
    }
)

#: The status an optimistic UI patch reports for each activity a command leads to.
CANONICAL_STATUSES: Mapping[VacuumActivity, StatusSlug] = MappingProxyType(
    {
        VacuumActivity.CLEANING: StatusSlug.SWEEPING,
        VacuumActivity.PAUSED: StatusSlug.PAUSED,
        VacuumActivity.IDLE: StatusSlug.IDLE,
        VacuumActivity.RETURNING: StatusSlug.GO_CHARGING,
        VacuumActivity.DOCKED: StatusSlug.CHARGING,
    }
)
