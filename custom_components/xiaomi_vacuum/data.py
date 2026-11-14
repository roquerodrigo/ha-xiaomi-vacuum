"""Custom types for xiaomi_vacuum."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, NotRequired, Protocol, TypedDict

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import CustomCleaning, XiaomiVacuumApiClient
    from .coordinator import XiaomiVacuumDataUpdateCoordinator
    from .map_coordinator import XiaomiVacuumMapCoordinator
    from .spec import ModelSpec


type XiaomiVacuumConfigEntry = ConfigEntry[XiaomiVacuumData]

type JsonValue = (
    str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None
)
"""Any value representable in JSON (recursive)."""

type JsonObject = dict[str, JsonValue]
"""A JSON object — string keys to JSON values."""


class VacuumState(TypedDict):
    """
    Parsed MIoT state, keyed by the names in the active model's property mapping.

    Every key mirrors a ``ModelSpec.property_mapping`` entry and is built
    dynamically by ``XiaomiVacuumApiClient.async_get_state``. Fields are
    optional because the supported models expose different properties (e.g.
    the S20+ has no ``fault_ids`` / ``sweep_route`` / ``obstacle_avoidance``).
    ``fault`` and ``fault_text`` are derived by the coordinator from the live
    fault payload.
    """

    status: int | None
    task_status: NotRequired[int | None]
    sweep_mop_type: NotRequired[int | None]
    cleaning_area: NotRequired[int | None]
    cleaning_time: NotRequired[int | None]
    clean_times: NotRequired[int | None]
    fan_speed: NotRequired[int | None]
    mop_water_level: NotRequired[int | None]
    mop_status: NotRequired[bool | None]
    room_information: NotRequired[str | None]
    last_clean_time: NotRequired[int | None]
    map_obj_name: NotRequired[str | None]
    sweep_route: NotRequired[int | None]
    obstacle_avoidance_strategy: NotRequired[int | None]
    battery_level: NotRequired[int | None]
    charging_state: NotRequired[int | None]
    mop_life: NotRequired[int | None]
    main_brush_life: NotRequired[int | None]
    side_brush_life: NotRequired[int | None]
    filter_life: NotRequired[int | None]
    main_brush_time_left: NotRequired[int | None]
    side_brush_time_left: NotRequired[int | None]
    filter_time_left: NotRequired[int | None]
    mop_time_left: NotRequired[int | None]
    drying_time_left: NotRequired[int | None]
    total_clean_time: NotRequired[int | None]
    total_clean_count: NotRequired[int | None]
    total_clean_area: NotRequired[int | None]
    child_lock: NotRequired[int | None]
    carpet_boost: NotRequired[int | None]
    resume_after_charge: NotRequired[int | None]
    do_not_disturb: NotRequired[bool | None]
    volume: NotRequired[int | None]
    mop_wash: NotRequired[bool | None]
    mop_wash_frequency: NotRequired[int | None]
    mop_wash_area_interval: NotRequired[int | None]
    mop_wash_time_interval: NotRequired[int | None]
    mop_drying_time: NotRequired[int | None]
    auto_dust_collection: NotRequired[bool | None]
    auto_mop_drying: NotRequired[bool | None]
    # Live fault payload: a JSON fault-ids list (X20 Max) or a plain code (S20+).
    fault_ids: NotRequired[str | None]
    fault: NotRequired[int | None]
    fault_text: NotRequired[str]


class MapCalibration(TypedDict):
    """
    Geometry that maps rendered-map pixels back to device millimetres.

    ``origin_x`` / ``origin_y`` anchor the device grid, ``resolution`` is the
    millimetres per grid cell, ``width`` / ``height`` the grid size, and
    ``scale`` / ``border`` how the renderer enlarged and padded the grid.
    """

    origin_x: float
    origin_y: float
    resolution: float
    width: int
    height: int
    scale: float
    border: int


class MapRoom(TypedDict):
    """A named room decoded from the map, keyed by the id room-clean takes."""

    id: str
    name: str


class RenderedMap(TypedDict):
    """One rendered map: the PNG, the calibration its render used, its rooms."""

    png: bytes
    # None for a PNG restored from a cache written before calibration existed.
    calibration: MapCalibration | None
    # Named rooms carried by the map itself (Dreame format); the Xiaomi models
    # publish theirs in a property instead, so their maps carry none.
    rooms: NotRequired[list[MapRoom]]


class CloudSessionTokens(TypedDict):
    """Xiaomi cloud session tokens persisted in the config entry."""

    ssecurity: str | None
    service_token: str | None
    user_id: str | None


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


@dataclass
class XiaomiVacuumData:
    """Data for the Xiaomi Vacuum integration."""

    client: XiaomiVacuumApiClient
    coordinator: XiaomiVacuumDataUpdateCoordinator
    integration: Integration
    info: DeviceInfoLike
    spec: ModelSpec
    map_coordinator: XiaomiVacuumMapCoordinator | None = None
    custom_cleanings: tuple[CustomCleaning, ...] = ()
