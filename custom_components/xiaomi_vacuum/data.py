"""Custom types for xiaomi_vacuum."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import XiaomiVacuumApiClient
    from .coordinator import XiaomiVacuumDataUpdateCoordinator


type XiaomiVacuumConfigEntry = ConfigEntry[XiaomiVacuumData]


@dataclass
class XiaomiVacuumData:
    """Data for the Xiaomi Vacuum integration."""

    client: XiaomiVacuumApiClient
    coordinator: XiaomiVacuumDataUpdateCoordinator
    integration: Integration
    info: Any
