"""Room cleaning by marking the rooms, then starting a custom sweep."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ...const import LOGGER  # noqa: TID252
from .room_cleaning import RoomCleaning
from .room_cleaning_error import RoomCleaningError

if TYPE_CHECKING:
    from ...data import JsonObject  # noqa: TID252
    from ..addresses import MiotActionAddress  # noqa: TID252
    from .room_cleaning_device import RoomCleaningDevice


@dataclass(frozen=True)
class ConfigThenCustomSweep(RoomCleaning):
    """
    Mark the rooms' ``on`` flags, then fire ``start-custom-sweep``.

    Captured from the Mi Home app on the S20+, whose spec-published direct room
    sweep is ignored by the robot. Both steps go through the cloud when a session
    is available: local UDP routinely times out on the multi-step sequence, and a
    lost first step would leave the second one cleaning the wrong rooms.
    """

    set_room_clean_configs: MiotActionAddress
    start_custom_sweep: MiotActionAddress

    @property
    def actions(self) -> tuple[MiotActionAddress, ...]:
        """The room-config and custom-sweep actions."""
        return (self.set_room_clean_configs, self.start_custom_sweep)

    async def async_start(
        self,
        device: RoomCleaningDevice,
        segment_ids: list[str],
        room_information: str | None,
    ) -> None:
        """Mark the requested rooms in the device's room config, then start."""
        config = _build_room_clean_config(room_information, segment_ids)
        if not config:
            msg = (
                "Cannot start room clean: the device published no room "
                "information. Configure rooms in the Mi Home app first."
            )
            raise RoomCleaningError(msg)
        LOGGER.debug(
            "Calling set-room-clean-configs (%s/%s) with %d room(s), cleaning %d",
            self.set_room_clean_configs["siid"],
            self.set_room_clean_configs["aiid"],
            len(config),
            sum(1 for room in config if room.get("on")),
        )
        await device.async_call_action_reliably(
            self.set_room_clean_configs, [json.dumps({"room_attrs": config})]
        )
        LOGGER.debug(
            "Calling start-custom-sweep (%s/%s)",
            self.start_custom_sweep["siid"],
            self.start_custom_sweep["aiid"],
        )
        await device.async_call_action_reliably(self.start_custom_sweep, [])


# Columns published by the S20+ `room-info` property (SIID 6 / piid 10) and
# accepted by `set-room-clean-configs` (SIID 2 / aiid 10). Order matters: the
# device publishes a table `room_attrs` whose first row is exactly this header.
_ROOM_ATTR_HEADERS = (
    "id",
    "room_name",
    "fan_level",
    "water_level",
    "clean_mode",
    "clean_times",
    "mop_mode",
    "on",
)


def _build_room_clean_config(
    room_information: str | None, segment_ids: list[str]
) -> list[JsonObject]:
    """
    Build the S20+ ``set-room-clean-configs`` payload.

    Reads the current room config from ``room_information`` (the device's
    table-shaped ``room_attrs`` JSON), converts it to the object-array write
    format the action expects, and flips the ``on`` flag to True for every
    requested room id (False for the rest). Returns an empty list when the
    device published no rooms (caller should refuse to start in that case).

    The order of selected rooms is preserved from ``segment_ids``: the Mi Home
    app stores the cleaning sequence as the position of each room in
    ``room_attrs``, so we emit the requested rooms first (in the order the
    caller asked for), followed by the unselected ones in their original
    relative order. A ``clean_area`` call with ``[kitchen, living_room]`` thus
    cleans kitchen before living_room.
    """
    if not room_information:
        return []
    try:
        data = json.loads(room_information)
    except ValueError, TypeError:
        return []
    matrix = data.get("room_attrs") if isinstance(data, dict) else None
    if not isinstance(matrix, list) or not matrix:
        return []
    header = matrix[0] if isinstance(matrix[0], list) else list(_ROOM_ATTR_HEADERS)
    # Normalise header cells to lower-case, matching ``_rows_to_attrs`` in
    # ``vacuum/cleaner.py``: both parsers read the same ``room_attrs`` payload,
    # so a device publishing ``Id`` / ``Room_Name`` instead of the lower-case
    # spelling resolves identically in both places. Without this the per-room
    # ``id`` lookup below fails on every row and the config comes back empty.
    header = [str(c).casefold() if c is not None else "" for c in header]
    # Requested sequence as an ordered lookup: position decides emit order.
    wanted_order = [str(s) for s in segment_ids]
    wanted = set(wanted_order)
    selected: list[JsonObject] = []
    others: list[JsonObject] = []
    for row in matrix[1:]:
        if not isinstance(row, list):
            continue
        room = dict(zip(header, row, strict=False))
        room_id = room.get("id")
        if room_id is None:
            continue
        room_id_str = str(room_id)
        room["on"] = room_id_str in wanted
        if room["on"]:
            selected.append(room)
        else:
            others.append(room)
    # Reorder selected rooms to match the requested sequence (stable for any
    # ids the device knows but the caller didn't list, which shouldn't happen).
    selected.sort(key=lambda r: _ordered_index(str(r.get("id")), wanted_order))
    return selected + others


def _ordered_index(room_id: str, wanted_order: list[str]) -> int:
    """Position of ``room_id`` in ``wanted_order``, or a large sentinel if absent."""
    try:
        return wanted_order.index(room_id)
    except ValueError:
        return len(wanted_order)
