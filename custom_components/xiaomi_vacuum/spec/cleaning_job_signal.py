"""What a device status code reveals about the cleaning job."""

from __future__ import annotations

from enum import StrEnum


class CleaningJobSignal(StrEnum):
    """
    Whether a status code proves a cleaning job is running, over, or neither.

    Some statuses occur both mid-job and after it ends (the dock washing the mop
    between rooms and after the last one both report ``station_working``), so
    they cannot decide the job on their own and leave the previous verdict in
    place.
    """

    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    INCONCLUSIVE = "inconclusive"
