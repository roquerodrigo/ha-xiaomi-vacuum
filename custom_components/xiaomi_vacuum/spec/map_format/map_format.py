"""How a model encodes its cloud map blob."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xiaomi_vacuum_sdk import MapRenderer, RenderedMap


class MapFormat(ABC):
    """Draws a model's map blob and says where its room list comes from."""

    @property
    @abstractmethod
    def carries_rooms(self) -> bool:
        """Whether the map lists the rooms, instead of the room-information property."""

    @abstractmethod
    def render(
        self, renderer: MapRenderer, raw: bytes, *, model: str, device_id: str
    ) -> RenderedMap | None:
        """Decode and draw ``raw``, or None when the payload holds no drawable map."""
