"""Room cleaning through one action that takes the room ids."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ...const import LOGGER  # noqa: TID252
from .room_cleaning import RoomCleaning

if TYPE_CHECKING:
    from ...data import JsonValue  # noqa: TID252
    from ..addresses import MiotActionAddress, MiotActionInputAddress  # noqa: TID252
    from .room_cleaning_device import RoomCleaningDevice


@dataclass(frozen=True)
class DirectRoomSweep(RoomCleaning):
    """``start-vacuum-room-sweep`` with the room ids as a comma-separated string."""

    action: MiotActionInputAddress

    @property
    def actions(self) -> tuple[MiotActionAddress, ...]:
        """The room-sweep action."""
        return (self.action,)

    async def async_start(
        self,
        device: RoomCleaningDevice,
        segment_ids: list[str],
        room_information: str | None,  # noqa: ARG002
    ) -> None:
        """Fire the room sweep with the requested rooms."""
        payload: list[JsonValue] = [
            {
                "piid": self.action["in_piid"],
                "value": ",".join(str(room) for room in segment_ids),
            }
        ]
        LOGGER.debug("Calling start-vacuum-room-sweep with payload: %s", payload)
        await device.async_call_action_with_params(self.action, payload)
