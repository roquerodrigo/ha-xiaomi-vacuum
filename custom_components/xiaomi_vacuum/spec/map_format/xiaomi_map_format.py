"""The encrypted Xiaomi map payload."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from xiaomi_vacuum_sdk import MapParseError

from ...const import LOGGER  # noqa: TID252
from .map_format import MapFormat

if TYPE_CHECKING:
    from xiaomi_vacuum_sdk import MapRenderer, RenderedMap


class XiaomiMapFormat(MapFormat):
    """An encrypted JSON map, keyed by the model and device id."""

    carries_rooms: ClassVar[bool] = False

    def render(
        self, renderer: MapRenderer, raw: bytes, *, model: str, device_id: str
    ) -> RenderedMap | None:
        """
        Decrypt, parse and draw the payload.

        A payload that parses to no map (e.g. a fresh map still being built) is
        not drawable; one that fails to decrypt is a real error and propagates.
        """
        try:
            return renderer.render_map(raw, model=model, device_id=device_id)
        except MapParseError as exception:
            LOGGER.debug("Map payload not drawable: %s", exception)
            return None
