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
    # Live fault payload — the raw shape depends on the model's fault_kind:
    # "ids" (X20 Max) → a JSON string; "simple" (S20+) → an int.
    fault_ids: NotRequired[str | None]
    fault: NotRequired[int | None]
    fault_text: NotRequired[str]


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
    spec: ModelSpec
    map_coordinator: XiaomiVacuumMapCoordinator | None = None
