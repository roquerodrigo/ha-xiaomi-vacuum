"""Vacuum platform for xiaomi_vacuum."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from homeassistant.components.vacuum import (
    Segment,
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)

from .const import (
    CHARGING_STATE_SLUGS,
    DOMAIN,
    FAN_SPEED_NAMES,
    FAN_SPEEDS,
    LOGGER,
    STATUS_SLUGS,
    STATUS_TO_ACTIVITY,
)
from .entity import XiaomiVacuumEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import XiaomiVacuumDataUpdateCoordinator
    from .data import XiaomiVacuumConfigEntry

SUPPORTED_FEATURES = (
    VacuumEntityFeature.START
    | VacuumEntityFeature.PAUSE
    | VacuumEntityFeature.STOP
    | VacuumEntityFeature.RETURN_HOME
    | VacuumEntityFeature.LOCATE
    | VacuumEntityFeature.FAN_SPEED
    | VacuumEntityFeature.BATTERY
    | VacuumEntityFeature.STATE
    | VacuumEntityFeature.CLEAN_AREA
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: XiaomiVacuumConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the vacuum entity."""
    async_add_entities([XiaomiVacuum(coordinator=entry.runtime_data.coordinator)])


class XiaomiVacuum(XiaomiVacuumEntity, StateVacuumEntity):
    """Xiaomi Vacuum entity."""

    _attr_name = None
    _attr_supported_features = SUPPORTED_FEATURES
    _attr_translation_key = "xiaomi_vacuum"

    def __init__(self, coordinator: XiaomiVacuumDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.config_entry.entry_id
        self._attr_fan_speed_list = list(FAN_SPEEDS)

    @property
    def _client(self) -> Any:
        return self.coordinator.config_entry.runtime_data.client

    @property
    def activity(self) -> VacuumActivity | None:
        """Return current activity (cleaning/docked/etc.)."""
        status = self.coordinator.data.get("status")
        if status is None:
            return None
        return STATUS_TO_ACTIVITY.get(int(status))

    @property
    def battery_level(self) -> int | None:
        """Return battery level 0-100."""
        level = self.coordinator.data.get("battery_level")
        return int(level) if level is not None else None

    @property
    def fan_speed(self) -> str | None:
        """Return current fan speed label."""
        speed = self.coordinator.data.get("fan_speed")
        return FAN_SPEED_NAMES.get(int(speed)) if speed is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose raw MIoT properties as diagnostic attributes."""
        data = self.coordinator.data
        attrs: dict[str, Any] = {
            "status_code": data.get("status"),
            "status": STATUS_SLUGS.get(data.get("status") or -1),
            "fault_code": data.get("fault"),
            "cleaning_area": data.get("cleaning_area"),
            "cleaning_time": data.get("cleaning_time"),
            "last_clean_time": data.get("last_clean_time"),
            "mop_water_level": data.get("mop_water_level"),
            "charging_state": CHARGING_STATE_SLUGS.get(
                data.get("charging_state") or -1
            ),
            "room_information_raw": data.get("room_information"),
        }
        return {DOMAIN: attrs}

    async def async_start(self) -> None:
        """Start cleaning."""
        await self._client.async_start()
        self._patch_state(status=4)
        self._schedule_refresh()

    async def async_pause(self) -> None:
        """Pause cleaning."""
        await self._client.async_pause()
        self._patch_state(status=5)
        self._schedule_refresh()

    async def async_stop(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Stop cleaning."""
        await self._client.async_stop()
        self._patch_state(status=1)
        self._schedule_refresh()

    async def async_return_to_base(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Return to dock."""
        await self._client.async_return_home()
        self._patch_state(status=6)
        self._schedule_refresh()

    async def async_locate(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Beep + light on the device."""
        await self._client.async_locate()

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:  # noqa: ARG002
        """Set fan speed by label."""
        await self._client.async_set_fan_speed(fan_speed)
        if (code := FAN_SPEEDS.get(fan_speed)) is not None:
            self._patch_state(fan_speed=code)
        self._schedule_refresh()

    async def async_get_segments(self) -> list[Segment]:
        """Return the rooms reported by the vacuum (for HA's area mapping UI)."""
        raw = self.coordinator.data.get("room_information")
        return _parse_segments(raw)

    async def async_clean_segments(
        self,
        segment_ids: list[str],
        **kwargs: Any,  # noqa: ARG002
    ) -> None:
        """Clean specific segments by ID."""
        await self._client.async_clean_segments(segment_ids)
        self._patch_state(status=4)
        self._schedule_refresh()


def _parse_segments(raw: Any) -> list[Segment]:
    """Parse d109gl `room-information` (string) into Segment objects (JSON expected)."""
    if not raw:
        return []
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):  # fmt: skip
        LOGGER.warning("Could not JSON-parse room_information: %r", raw)
        return []

    rooms: list[dict[str, Any]] = []
    if isinstance(data, list):
        rooms = [r for r in data if isinstance(r, dict)]
    elif isinstance(data, dict):
        for key in ("rooms", "list", "data"):
            if isinstance(data.get(key), list):
                rooms = [r for r in data[key] if isinstance(r, dict)]
                break

    segments: list[Segment] = []
    for room in rooms:
        room_id = room.get("id") or room.get("roomId") or room.get("room_id")
        name = room.get("name") or room.get("roomName") or room.get("room_name")
        if room_id is None or name is None:
            continue
        segments.append(Segment(id=str(room_id), name=str(name)))

    if not segments:
        LOGGER.warning("No segments parsed from room_information; raw payload: %r", raw)
    return segments
