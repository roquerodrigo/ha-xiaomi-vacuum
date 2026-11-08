"""The Dreame map frame."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from xiaomi_vacuum_sdk import DreameMapDecoder, MapError

from ...const import LOGGER  # noqa: TID252
from .map_format import MapFormat

if TYPE_CHECKING:
    from xiaomi_vacuum_sdk import MapRenderer, RenderedMap


class DreameMapFormat(MapFormat):
    """A pixel grid plus a JSON trailer whose segment metadata lists the rooms."""

    carries_rooms: ClassVar[bool] = True

    def render(
        self,
        renderer: MapRenderer,
        raw: bytes,
        *,
        model: str,  # noqa: ARG002
        device_id: str,  # noqa: ARG002
    ) -> RenderedMap | None:
        """Decode the frame and draw it, or None when it is not drawable yet."""
        try:
            map_data = DreameMapDecoder().decode(raw)
        except MapError as exception:
            # E.g. an encrypted frame.
            LOGGER.debug("Dreame map payload not drawable: %s", exception)
            return None
        return renderer.render_map_data(map_data)
