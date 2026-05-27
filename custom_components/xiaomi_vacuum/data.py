"""Custom types for xiaomi_vacuum."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, NotRequired, Protocol, TypedDict

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import XiaomiVacuumApiClient
    from .coordinator import XiaomiVacuumDataUpdateCoordinator
    from .map_coordinator import XiaomiVacuumMapCoordinator


type XiaomiVacuumConfigEntry = ConfigEntry[XiaomiVacuumData]

type JsonValue = (
    str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
)
"""Any value representable in JSON (recursive)."""

type JsonObject = dict[str, JsonValue]
"""A JSON object — string keys to JSON values."""


class VacuumState(TypedDict):
    """
    Parsed MIoT state, keyed by the names in ``PROPERTY_MAPPING``.

    Every key mirrors a ``PROPERTY_MAPPING`` entry and is built dynamically by
    ``XiaomiVacuumApiClient.async_get_state``. ``fault`` and ``fault_text`` are
    derived by the coordinator from the live ``fault_ids`` payload.
    """

    status: int | None
    fault_ids: str | None
    sweep_mop_type: int | None
    cleaning_area: int | None
    cleaning_time: int | None
    clean_times: int | None
    fan_speed: int | None
    mop_water_level: int | None
    room_information: str | None
    last_clean_time: int | None
    map_obj_name: str | None
    sweep_route: int | None
    obstacle_avoidance_strategy: int | None
    battery_level: int | None
    charging_state: int | None
    mop_life: int | None
    side_brush_life: int | None
    filter_life: int | None
    dust_bag_life: int | None
    fault: int | None
    fault_text: NotRequired[str]


class DeviceInfoLike(Protocol):
    """Structural type for the python-miio handshake result we consume."""

    @property
    def model(self) -> str:
        """Device model string (e.g. ``xiaomi.vacuum.d109gl``)."""

    @property
    def mac_address(self) -> str | None:
        """Device MAC address, if reported."""

    @property
    def firmware_version(self) -> str | None:
        """Firmware version string, if reported."""

    @property
    def hardware_version(self) -> str | None:
        """Hardware revision string, if reported."""

    @property
    def raw(self) -> JsonObject:
        """Raw handshake payload, logged for diagnostics."""


@dataclass
class XiaomiVacuumData:
    """Data for the Xiaomi Vacuum integration."""

    client: XiaomiVacuumApiClient
    coordinator: XiaomiVacuumDataUpdateCoordinator
    integration: Integration
    info: DeviceInfoLike
    map_coordinator: XiaomiVacuumMapCoordinator | None = None
