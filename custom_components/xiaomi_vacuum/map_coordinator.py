"""Coordinator that periodically downloads & parses the vacuum map (cloud-only)."""

from __future__ import annotations

import base64
import contextlib
import io
import json
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from vacuum_map_parser_base.config.color import ColorsPalette, SupportedColor
from vacuum_map_parser_base.config.drawable import Drawable
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.config.size import Size, Sizes
from vacuum_map_parser_xiaomi.map_data_parser import XiaomiMapDataParser

from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from vacuum_map_parser_base.map_data import MapData

    from .cloud import XiaomiCloud
    from .coordinator import XiaomiVacuumDataUpdateCoordinator
    from .data import XiaomiVacuumConfigEntry

MAP_UPDATE_INTERVAL = timedelta(seconds=60)
DEFAULT_DRAWABLES: list[Drawable] = [
    Drawable.CHARGER,
    Drawable.PATH,
    Drawable.PREDICTED_PATH,
    Drawable.VACUUM_POSITION,
    Drawable.NO_GO_AREAS,
    Drawable.NO_MOPPING_AREAS,
    Drawable.VIRTUAL_WALLS,
    Drawable.ZONES,
]
DEFAULT_PALETTE = ColorsPalette(colors_dict={SupportedColor.MAP_OUTSIDE: (0, 0, 0, 0)})
DEFAULT_IMAGE_CONFIG = ImageConfig(scale=4.0)
DEFAULT_SIZES = Sizes(
    sizes={
        Size.VACUUM_RADIUS: 18,
        Size.PATH_WIDTH: 4,
        Size.CHARGER_RADIUS: 10,
    }
)


class XiaomiVacuumMapCoordinator(DataUpdateCoordinator[bytes | None]):
    """Polls the cloud for the latest map binary and renders it to PNG bytes."""

    config_entry: XiaomiVacuumConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        cloud: XiaomiCloud,
        state_coordinator: XiaomiVacuumDataUpdateCoordinator,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=f"{DOMAIN}_map",
            update_interval=MAP_UPDATE_INTERVAL,
        )
        self._cloud = cloud
        self._state_coordinator = state_coordinator
        self._last_raw: bytes | None = None
        self._parser = XiaomiMapDataParser(
            palette=DEFAULT_PALETTE,
            sizes=DEFAULT_SIZES,
            drawables=DEFAULT_DRAWABLES,
            image_config=DEFAULT_IMAGE_CONFIG,
            texts=[],
        )

    async def _async_update_data(self) -> bytes | None:
        raw_field = (self._state_coordinator.data or {}).get("map_obj_name")
        obj_name = self._extract_obj_name(raw_field)
        if not obj_name:
            LOGGER.debug("No map obj_name available; skipping map update")
            return self.data
        device = self._cloud._device  # noqa: SLF001
        if device is None:
            return self.data
        try:
            raw = await self._cloud.async_get_map_bytes(obj_name)
            LOGGER.debug("Map blob: obj=%s bytes=%s", obj_name, len(raw) if raw else 0)
            if not raw:
                return self.data
            if raw == self._last_raw:
                # Same blob as last poll — skip the (expensive) parse + render.
                return self.data
            self._last_raw = raw
            map_data = await self.hass.async_add_executor_job(
                self._parse_blob, raw, device.model, device.device_id
            )
            if not map_data or not getattr(map_data, "image", None):
                LOGGER.debug("Parser returned no image for obj=%s", obj_name)
                return self.data
            buf = io.BytesIO()
            map_data.image.data.save(buf, format="PNG")
        except Exception as exception:
            raise UpdateFailed(exception) from exception
        png = buf.getvalue()
        LOGGER.debug("Rendered PNG: %s bytes", len(png))
        return png

    def _parse_blob(self, raw: bytes, model: str, device_id: str) -> MapData:
        """Decrypt the binary map then parse the JSON it produces."""
        # Older firmwares wrap the binary in {"data": "<base64>"}.
        with contextlib.suppress(json.JSONDecodeError, KeyError, UnicodeDecodeError):
            raw = base64.decodebytes(json.loads(raw)["data"].encode("latin1"))
        # The decryptor uses the model string as a 16-byte AES key
        # (`xiaomi.vacuum.d109gl` → `mi.vacuum.d109gl`) and expects hex input.
        model_key = model.replace("xiaomi", "mi")
        decoded = self._parser.unpack_map(
            raw.hex(), model=model_key, device_id=str(device_id)
        )
        return self._parser.parse(decoded)

    @staticmethod
    def _extract_obj_name(raw_field: str | None) -> str | None:
        """Extract the inner obj_name from the MIoT property's JSON envelope."""
        if not raw_field:
            return None
        with contextlib.suppress(json.JSONDecodeError, ValueError, TypeError):
            payload = json.loads(raw_field)
            if isinstance(payload, dict) and (name := payload.get("obj_name")):
                return str(name)
        return raw_field if isinstance(raw_field, str) else None
