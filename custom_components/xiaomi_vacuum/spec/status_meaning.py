"""What one status means to Home Assistant."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.components.vacuum.const import VacuumActivity

    from .cleaning_job_signal import CleaningJobSignal


@dataclass(frozen=True)
class StatusMeaning:
    """
    The HA activity, idle flag and cleaning-job signal of one status.

    ``is_idle`` marks a parked robot a fresh clean can start from (anything else
    resumes the current job). ``cleaning_job`` says whether the status proves a
    job is running, over, or neither.
    """

    activity: VacuumActivity
    is_idle: bool
    cleaning_job: CleaningJobSignal
