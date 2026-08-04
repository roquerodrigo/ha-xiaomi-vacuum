"""Xiaomi vacuum entity for xiaomi_vacuum."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, TypedDict

from homeassistant.components.vacuum import (
    Segment,
    StateVacuumEntity,
)
from homeassistant.components.vacuum.const import (
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.exceptions import ServiceValidationError

from ..const import DOMAIN, LOGGER  # noqa: TID252
from ..entity import XiaomiVacuumEntity  # noqa: TID252

if TYPE_CHECKING:
    from ..api import XiaomiVacuumApiClient  # noqa: TID252
    from ..data import JsonValue, VacuumState  # noqa: TID252
    from ..spec import ModelSpec  # noqa: TID252


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

    @property
    def spec(self) -> ModelSpec:
        """The active model's spec."""
        return self.coordinator.spec

    @property
    def fan_speed_list(self) -> list[str]:
        """Return the fan speed labels supported by the active model."""
        return list(self.spec.fan_speeds)

    @property
    def unique_id(self) -> str:
        """Return a stable unique id for this entity."""
        return self.coordinator.config_entry.entry_id

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
        return self.spec.status_to_activity.get(int(status))

    @property
    def fan_speed(self) -> str | None:
        """Return current fan speed label."""
        speed = self.coordinator.data.get("fan_speed")
        return self.spec.fan_speed_names.get(int(speed)) if speed is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, _VacuumAttributes]:
        """Expose raw MIoT properties as diagnostic attributes."""
        data = self.coordinator.data
        status = data.get("status")
        charging_state = data.get("charging_state")
        attrs: _VacuumAttributes = {
            "status_code": data.get("status"),
            "status": (
                self.spec.status_slugs.get(status) if status is not None else None
            ),
            "fault_code": data.get("fault"),
            "cleaning_area": data.get("cleaning_area"),
            "cleaning_time": data.get("cleaning_time"),
            "last_clean_time": data.get("last_clean_time"),
            "mop_water_level": data.get("mop_water_level"),
            "charging_state": (
                self.spec.charging_state_slugs.get(charging_state)
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
        self._patch_state(status=self.spec.status_code_for(VacuumActivity.CLEANING))
        self._schedule_refresh()

    def _idle_at_dock(self) -> bool:
        """Whether the robot is parked/idle, so start begins a fresh clean."""
        return self.coordinator.data.get("status") in self.spec.idle_statuses

    async def async_pause(self) -> None:
        """Pause cleaning."""
        await self._client.async_pause()
        self._patch_state(status=self.spec.status_code_for(VacuumActivity.PAUSED))
        self._schedule_refresh()

    async def async_stop(self, **kwargs: object) -> None:  # noqa: ARG002
        """Stop cleaning."""
        await self._client.async_stop()
        self._patch_state(status=self.spec.status_code_for(VacuumActivity.IDLE))
        self._schedule_refresh()

    async def async_return_to_base(self, **kwargs: object) -> None:  # noqa: ARG002
        """Return to dock."""
        await self._client.async_return_home()
        self._patch_state(status=self.spec.status_code_for(VacuumActivity.RETURNING))
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
        """Invoke a whitelisted MIoT action by name (see spec.send_commands)."""
        send_commands = self.spec.send_commands
        action = send_commands.get(command)
        if action is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_send_command",
                translation_placeholders={
                    "command": command,
                    "valid_commands": ", ".join(send_commands),
                },
            )
        await self._client.async_call_action(action["siid"], action["aiid"])
        self._schedule_refresh()

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: object) -> None:  # noqa: ARG002
        """Set fan speed by label."""
        await self._client.async_set_fan_speed(fan_speed)
        if (code := self.spec.fan_speeds.get(fan_speed)) is not None:
            self._patch_state(fan_speed=code)
        self._schedule_refresh()

    async def async_get_segments(self) -> list[Segment]:
        """Return the rooms reported by the vacuum (for HA's area mapping UI)."""
        # Reached through the vacuum/get_segments websocket command, which does
        # not check availability — data is None while the robot has been
        # offline since startup (offline-tolerant setup).
        data: VacuumState | None = self.coordinator.data
        raw = data.get("room_information") if data else None
        return _parse_segments(raw)

    async def async_clean_segments(
        self,
        segment_ids: list[str],
        **kwargs: object,  # noqa: ARG002
    ) -> None:
        """Clean specific segments by ID."""
        await self._client.async_clean_segments(
            segment_ids,
            room_information=self.coordinator.data.get("room_information"),
        )
        self._patch_state(status=self.spec.status_code_for(VacuumActivity.CLEANING))
        self._schedule_refresh()


# Column/key aliases for room id and name across both payload shapes
# (object-array on the X20 Max, table/matrix on the S20+). Keys are matched
# verbatim against object-array dicts; for the table format the header row is
# case-folded first, so lowercase spellings cover both original and folded forms.
_ID_HEADERS = ("id", "room_id", "roomId", "roomid")
_NAME_HEADERS = ("room_name", "roomName", "name", "roomname")


def _parse_segments(raw: str | None) -> list[Segment]:
    """
    Parse `room-information` (string) into Segment objects.

    Two payload shapes are supported:

    * object array (X20 Max) — ``{"rooms": [{"id": 10, "name": "..."}]}`` or a
      bare list of such dicts;
    * table/matrix (S20+) — ``{"version": 2, "room_attrs": [[header...],
      [row...], ...]}`` where the first row names the columns (``id``,
      ``room_name``, …) and the rest are positional values.
    """
    if not raw:
        return []
    try:
        data: JsonValue = json.loads(raw)
    except ValueError, TypeError:
        LOGGER.warning("Could not JSON-parse room_information: %r", raw)
        return []

    rooms: list[dict[str, JsonValue]] = []
    if isinstance(data, list):
        rooms = [r for r in data if isinstance(r, dict)]
    elif isinstance(data, dict):
        if isinstance(data.get("room_attrs"), list):
            # S20+-style matrix payload: first row is the header, rest are rows.
            rooms = _rows_to_attrs(data["room_attrs"])
        else:
            for key in ("rooms", "list", "data"):
                value = data.get(key)
                if isinstance(value, list):
                    rooms = [r for r in value if isinstance(r, dict)]
                    break

    segments: list[Segment] = []
    for room in rooms:
        segment = _extract_segment(room)
        if segment is not None:
            segments.append(segment)

    if not segments:
        LOGGER.warning("No segments parsed from room_information; raw payload: %r", raw)
    return segments


def _rows_to_attrs(matrix: JsonValue) -> list[dict[str, JsonValue]]:
    """Turn an S20+ ``room_attrs`` matrix into per-room dicts keyed by header."""
    rows = (
        [r for r in matrix if isinstance(r, list)] if isinstance(matrix, list) else []
    )
    if not rows:
        return []
    # Header row: normalise to lower-case strings so lookups are forgiving.
    header = [str(col).casefold() if col is not None else "" for col in rows[0]]
    return [dict(zip(header, row, strict=False)) for row in rows[1:]]


def _extract_segment(room: dict[str, JsonValue]) -> Segment | None:
    """Pull a stable id + name out of one room dict, skipping unnamed rooms."""
    room_id = next((room[k] for k in _ID_HEADERS if room.get(k) is not None), None)
    name = next((room[k] for k in _NAME_HEADERS if room.get(k) is not None), None)
    # Skip rooms without an id or with a blank name — HA segments need a label
    # and unnamed rooms (common on the S20+ until the user names them in Mi Home)
    # only clutter the mapping dialog.
    if room_id is None or name is None or not str(name).strip():
        return None
    return Segment(id=str(room_id), name=str(name).strip())
