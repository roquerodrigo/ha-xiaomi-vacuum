"""Coordinator that periodically downloads & parses the vacuum map (cloud-only)."""

from __future__ import annotations

import base64
import contextlib
import io
import json
from datetime import timedelta
from typing import TYPE_CHECKING, cast

from homeassistant.helpers.storage import Store
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
MAP_STORAGE_VERSION = 1
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
DEFAULT_PALETTE = ColorsPalette(
    colors_dict={
        SupportedColor.MAP_OUTSIDE: (250, 249, 246, 0),
        SupportedColor.MAP_INSIDE: (92, 110, 84),
        SupportedColor.MAP_WALL: (92, 110, 84),
        SupportedColor.MAP_WALL_V2: (92, 110, 84),
        SupportedColor.GREY_WALL: (92, 110, 84),
        SupportedColor.PATH: (92, 110, 84),
        SupportedColor.PREDICTED_PATH: (92, 110, 84, 160),
        SupportedColor.GOTO_PATH: (92, 110, 84),
        SupportedColor.ZONES: (164, 172, 134, 100),
        SupportedColor.ZONES_OUTLINE: (45, 74, 43),
        SupportedColor.VIRTUAL_WALLS: (161, 68, 68),
        SupportedColor.NO_GO_ZONES: (161, 68, 68, 127),
        SupportedColor.NO_GO_ZONES_OUTLINE: (161, 68, 68),
        SupportedColor.NO_MOPPING_ZONES: (90, 117, 149, 127),
        SupportedColor.NO_MOPPING_ZONES_OUTLINE: (90, 117, 149),
        SupportedColor.CHARGER: (45, 74, 43, 220),
        SupportedColor.CHARGER_OUTLINE: (20, 34, 20),
        SupportedColor.ROBO: (255, 254, 250),
        SupportedColor.ROBO_OUTLINE: (20, 34, 20),
        SupportedColor.ROOM_NAMES: (20, 34, 20),
        SupportedColor.NEW_DISCOVERED_AREA: (210, 214, 188),
        SupportedColor.SCAN: (224, 227, 200),
        SupportedColor.CLEANED_AREA: (45, 74, 43, 80),
        SupportedColor.CARPETS: (170, 186, 170),
        SupportedColor.NO_CARPET_ZONES: (192, 133, 64, 127),
        SupportedColor.NO_CARPET_ZONES_OUTLINE: (192, 133, 64),
        SupportedColor.MOP_PATH: (255, 254, 250, 72),
    },
    room_colors={
        "1": (214, 196, 168),
        "2": (180, 198, 210),
        "3": (196, 202, 164),
        "4": (204, 192, 210),
        "5": (220, 204, 170),
        "6": (186, 210, 206),
        "7": (212, 194, 196),
        "8": (190, 200, 216),
        "9": (200, 190, 174),
        "10": (186, 210, 206),
        "11": (214, 196, 168),
        "12": (196, 202, 164),
        "13": (204, 192, 210),
        "14": (220, 204, 170),
        "15": (180, 198, 210),
        "16": (212, 194, 196),
        "17": (190, 200, 216),
        "18": (200, 190, 174),
        "19": (186, 210, 206),
        "20": (196, 202, 164),
        "21": (214, 196, 168),
        "22": (204, 192, 210),
        "23": (220, 204, 170),
        "24": (180, 198, 210),
        "25": (212, 194, 196),
        "26": (200, 190, 174),
        "27": (196, 202, 164),
        "28": (186, 210, 206),
        "29": (214, 196, 168),
        "30": (204, 192, 210),
        "31": (220, 204, 170),
        "32": (180, 198, 210),
    },
)
DEFAULT_IMAGE_CONFIG = ImageConfig(scale=8.0)
DEFAULT_SIZES = Sizes(
    sizes={
        Size.VACUUM_RADIUS: 18,
        Size.PATH_WIDTH: 2,
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
            config_entry=state_coordinator.config_entry,
        )
        self._cloud = cloud
        self._state_coordinator = state_coordinator
        self._last_raw: bytes | None = None
        self._store: Store[dict[str, str]] = Store(
            hass,
            MAP_STORAGE_VERSION,
            f"{DOMAIN}.map_{state_coordinator.config_entry.entry_id}",
        )
        self._parser = XiaomiMapDataParser(
            palette=DEFAULT_PALETTE,
            sizes=DEFAULT_SIZES,
            drawables=DEFAULT_DRAWABLES,
            image_config=DEFAULT_IMAGE_CONFIG,
            texts=[],
        )

    async def async_load_cached(self) -> None:
        """Restore the last rendered map PNG from disk so it survives restarts."""
        stored = await self._store.async_load()
        if not stored:
            return
        try:
            png = base64.b64decode(stored["png_b64"], validate=True)
        except (KeyError, ValueError) as exception:
            LOGGER.warning("Discarding corrupt cached map: %s", exception)
            return
        LOGGER.debug("Restored cached map PNG: %s bytes", len(png))
        self.async_set_updated_data(png)

    async def _async_update_data(self) -> bytes | None:
        # State is None while the robot has been offline since startup; keep
        # serving whatever we have (possibly the disk-restored PNG).
        state = self._state_coordinator.data
        obj_name = self._extract_obj_name(state.get("map_obj_name")) if state else None
        device = self._cloud._device  # noqa: SLF001
        if not obj_name or device is None:
            LOGGER.debug("No map obj_name or cloud device; skipping map update")
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
            if (
                map_data is None
                or map_data.image is None
                or map_data.image.data is None
            ):
                LOGGER.debug("Parser returned no image for obj=%s", obj_name)
                return self.data
            buf = io.BytesIO()
            map_data.image.data.save(buf, format="PNG")
        except Exception as exception:
            raise UpdateFailed(exception) from exception
        png = buf.getvalue()
        LOGGER.debug("Rendered PNG: %s bytes", len(png))
        await self._store.async_save({"png_b64": base64.b64encode(png).decode()})
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
        return cast("MapData", self._parser.parse(decoded))

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
