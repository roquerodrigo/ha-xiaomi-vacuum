"""Room cleaning through the Dreame ``start-clean`` segment mode."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ...const import LOGGER  # noqa: TID252
from ..property import Property  # noqa: TID252
from .room_cleaning import RoomCleaning
from .room_cleaning_error import RoomCleaningError

if TYPE_CHECKING:
    from ...data import JsonValue  # noqa: TID252
    from ..addresses import MiotActionAddress, MiotSegmentCleanAddress  # noqa: TID252
    from .room_cleaning_device import RoomCleaningDevice

_SEGMENT_WORK_MODE = 18
_REPEATS_PER_ROOM = 1


@dataclass(frozen=True)
class DreameSegmentClean(RoomCleaning):
    """
    The segment work mode plus a ``{"selects": [[room, repeat, fan, water, order]]}``.

    Dreame-built models acknowledge their spec-published ``start-room-sweep`` but
    ignore it; this is the flow their app uses.
    """

    action: MiotSegmentCleanAddress

    @property
    def actions(self) -> tuple[MiotActionAddress, ...]:
        """The Dreame ``start-clean`` action."""
        return (self.action,)

    async def async_start(
        self,
        device: RoomCleaningDevice,
        segment_ids: list[str],
        room_information: str | None,  # noqa: ARG002
    ) -> None:
        """Clean the rooms in order with the current fan speed and water level."""
        try:
            rooms = [int(segment_id) for segment_id in segment_ids]
        except ValueError as exception:
            msg = f"Failed to clean rooms: invalid room id in {segment_ids}"
            raise RoomCleaningError(msg) from exception
        # The selection repeats the fan speed and water level per room; the
        # current settings keep the clean consistent with the app's choice.
        settings = await device.async_read_properties(
            (Property.FAN_SPEED, Property.MOP_WATER_LEVEL)
        )
        fan = settings.get(Property.FAN_SPEED)
        water = settings.get(Property.MOP_WATER_LEVEL)
        if fan is None or water is None:
            msg = "Failed to clean rooms: could not read the fan speed and water level"
            raise RoomCleaningError(msg)
        selects: list[JsonValue] = [
            [room, _REPEATS_PER_ROOM, fan, water, order]
            for order, room in enumerate(rooms, start=1)
        ]
        payload: list[JsonValue] = [
            {"piid": self.action["mode_piid"], "value": _SEGMENT_WORK_MODE},
            {
                "piid": self.action["data_piid"],
                "value": json.dumps({"selects": selects}, separators=(",", ":")),
            },
        ]
        LOGGER.debug("Calling Dreame start-clean with payload: %s", payload)
        await device.async_call_action_with_params(self.action, payload)
