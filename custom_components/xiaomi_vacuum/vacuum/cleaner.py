"""Xiaomi vacuum entity for xiaomi_vacuum."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, TypedDict

from homeassistant.components.vacuum import (
    Segment,
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.exceptions import ServiceValidationError

from ..const import (  # noqa: TID252
    CHARGING_STATE_SLUGS,
    DOMAIN,
    FAN_SPEED_NAMES,
    FAN_SPEEDS,
    IDLE_STATUSES,
    LOGGER,
    SEND_COMMANDS,
    STATUS_SLUGS,
    STATUS_TO_ACTIVITY,
)
from ..entity import XiaomiVacuumEntity  # noqa: TID252

if TYPE_CHECKING:
    from ..api import XiaomiVacuumApiClient  # noqa: TID252
    from ..coordinator import XiaomiVacuumDataUpdateCoordinator  # noqa: TID252
    from ..data import JsonValue  # noqa: TID252


class _VacuumAttributes(TypedDict):
    """Diagnostic attributes exposed under the integration's domain key."""

    status_code: int | None
    status: str | None
    fault_code: int | None
    cleaning_area: int | None
    cleaning_time: int | None
    last_clean_time: int | None
    mop_water_level: int | None
    charging_state: str | None
    room_information_raw: str | None


SUPPORTED_FEATURES = (
    VacuumEntityFeature.START
    | VacuumEntityFeature.PAUSE
    | VacuumEntityFeature.STOP
    | VacuumEntityFeature.RETURN_HOME
    | VacuumEntityFeature.LOCATE
    | VacuumEntityFeature.FAN_SPEED
    | VacuumEntityFeature.STATE
    | VacuumEntityFeature.CLEAN_AREA
    | VacuumEntityFeature.SEND_COMMAND
)


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
    def _client(self) -> XiaomiVacuumApiClient:
        """Return the local MIoT client backing this entity's commands."""
        return self.coordinator.config_entry.runtime_data.client

    @property
    def activity(self) -> VacuumActivity | None:
        """Return current activity; an active fault forces the ERROR state."""
        fault = self.coordinator.data.get("fault")
        if isinstance(fault, int) and fault != 0:
            return VacuumActivity.ERROR
        status = self.coordinator.data.get("status")
        if status is None:
            return None
        return STATUS_TO_ACTIVITY.get(int(status))

    @property
    def fan_speed(self) -> str | None:
        """Return current fan speed label."""
        speed = self.coordinator.data.get("fan_speed")
        return FAN_SPEED_NAMES.get(int(speed)) if speed is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, _VacuumAttributes]:
        """Expose raw MIoT properties as diagnostic attributes."""
        data = self.coordinator.data
        status = data.get("status")
        charging_state = data.get("charging_state")
        attrs: _VacuumAttributes = {
            "status_code": data.get("status"),
            "status": STATUS_SLUGS.get(status) if status is not None else None,
            "fault_code": data.get("fault"),
            "cleaning_area": data.get("cleaning_area"),
            "cleaning_time": data.get("cleaning_time"),
            "last_clean_time": data.get("last_clean_time"),
            "mop_water_level": data.get("mop_water_level"),
            "charging_state": (
                CHARGING_STATE_SLUGS.get(charging_state)
                if charging_state is not None
                else None
            ),
            "room_information_raw": data.get("room_information"),
        }
        return {DOMAIN: attrs}

    async def async_start(self) -> None:
        """
        Begin a fresh clean when parked/idle; otherwise resume the current job.

        Resuming everywhere else (Continue Sweep) is a no-op when there is nothing
        to resume, so a robot that finished but failed to dock is never restarted
        from scratch. Automations that should only ever resume can call the
        ``continue_sweep`` send_command directly.
        """
        if self._idle_at_dock():
            await self._client.async_start()
        else:
            await self._client.async_continue()
        self._patch_state(status=4)
        self._schedule_refresh()

    def _idle_at_dock(self) -> bool:
        """Whether the robot is parked/idle, so start begins a fresh clean."""
        return self.coordinator.data.get("status") in IDLE_STATUSES

    async def async_pause(self) -> None:
        """Pause cleaning."""
        await self._client.async_pause()
        self._patch_state(status=5)
        self._schedule_refresh()

    async def async_stop(self, **kwargs: object) -> None:  # noqa: ARG002
        """Stop cleaning."""
        await self._client.async_stop()
        self._patch_state(status=1)
        self._schedule_refresh()

    async def async_return_to_base(self, **kwargs: object) -> None:  # noqa: ARG002
        """Return to dock."""
        await self._client.async_return_home()
        self._patch_state(status=6)
        self._schedule_refresh()

    async def async_locate(self, **kwargs: object) -> None:  # noqa: ARG002
        """Beep + light on the device."""
        await self._client.async_locate()

    async def async_send_command(
        self,
        command: str,
        params: dict[str, object] | list[object] | None = None,  # noqa: ARG002
        **kwargs: object,  # noqa: ARG002
    ) -> None:
        """Invoke a whitelisted MIoT action by name (see SEND_COMMANDS)."""
        action = SEND_COMMANDS.get(command)
        if action is None:
            valid = ", ".join(SEND_COMMANDS)
            msg = f"Unknown command '{command}'. Valid commands: {valid}"
            raise ServiceValidationError(msg)
        await self._client.async_call_action(action["siid"], action["aiid"])
        self._schedule_refresh()

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: object) -> None:  # noqa: ARG002
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
        **kwargs: object,  # noqa: ARG002
    ) -> None:
        """Clean specific segments by ID."""
        await self._client.async_clean_segments(segment_ids)
        self._patch_state(status=4)
        self._schedule_refresh()


def _parse_segments(raw: str | None) -> list[Segment]:
    """Parse d109gl `room-information` (string) into Segment objects (JSON expected)."""
    if not raw:
        return []
    try:
        data: JsonValue = json.loads(raw)
    except (ValueError, TypeError):  # fmt: skip
        LOGGER.warning("Could not JSON-parse room_information: %r", raw)
        return []

    rooms: list[dict[str, JsonValue]] = []
    if isinstance(data, list):
        rooms = [r for r in data if isinstance(r, dict)]
    elif isinstance(data, dict):
        for key in ("rooms", "list", "data"):
            value = data.get(key)
            if isinstance(value, list):
                rooms = [r for r in value if isinstance(r, dict)]
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
