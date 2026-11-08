"""How a model starts cleaning a set of rooms."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..addresses import MiotActionAddress  # noqa: TID252
    from .room_cleaning_device import RoomCleaningDevice


class RoomCleaning(ABC):
    """
    One way of starting a room clean, carrying the actions it invokes.

    Models differ in which action cleans rooms and what it takes, and the Mi Home
    app often uses a different flow than the spec suggests, so each flow is its
    own class and a model picks one with its addresses.
    """

    @property
    @abstractmethod
    def actions(self) -> tuple[MiotActionAddress, ...]:
        """Every action the flow invokes."""

    @abstractmethod
    async def async_start(
        self,
        device: RoomCleaningDevice,
        segment_ids: list[str],
        room_information: str | None,
    ) -> None:
        """Start cleaning ``segment_ids`` in the given order."""
