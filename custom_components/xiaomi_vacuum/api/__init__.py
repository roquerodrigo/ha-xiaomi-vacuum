"""Local MIoT API client package for xiaomi_vacuum."""

from __future__ import annotations

from .cleaning_zone import CleaningZone
from .client import XiaomiVacuumApiClient
from .custom_cleaning import CustomCleaning
from .errors import (
    XiaomiVacuumApiClientCommunicationError,
    XiaomiVacuumApiClientError,
)

__all__ = [
    "CleaningZone",
    "CustomCleaning",
    "XiaomiVacuumApiClient",
    "XiaomiVacuumApiClientCommunicationError",
    "XiaomiVacuumApiClientError",
]
