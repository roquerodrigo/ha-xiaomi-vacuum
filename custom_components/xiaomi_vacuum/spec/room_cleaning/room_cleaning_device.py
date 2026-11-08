"""What a room-cleaning flow needs from the device connection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

    from xiaomi_vacuum_sdk import PropertyValue

    from ...data import JsonValue  # noqa: TID252
    from ..addresses import MiotActionAddress  # noqa: TID252
    from ..property import Property  # noqa: TID252


class RoomCleaningDevice(Protocol):
    """The device operations a :class:`RoomCleaning` flow is built from."""

    async def async_call_action_with_params(
        self, action: MiotActionAddress, params: list[JsonValue]
    ) -> None:
        """Invoke an action locally, tolerating the device's late acks."""

    async def async_call_action_reliably(
        self, action: MiotActionAddress, params: list[str]
    ) -> None:
        """Invoke an action through the cloud when available, else locally."""

    async def async_read_properties(
        self, names: Sequence[Property]
    ) -> dict[str, PropertyValue]:
        """Read the current value of the mapped properties among ``names``."""
