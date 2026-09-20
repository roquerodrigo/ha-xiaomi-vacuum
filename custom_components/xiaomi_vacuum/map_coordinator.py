"""Coordinator that periodically downloads & renders the vacuum map (cloud-only)."""

from __future__ import annotations

import base64
import contextlib
import json
from datetime import timedelta
from typing import TYPE_CHECKING, NotRequired, TypedDict

from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from xiaomi_vacuum_sdk import MapParseError, MapRenderer, RenderOptions
from xiaomi_vacuum_sdk.map.blob_decryptor import BlobDecryptor
from xiaomi_vacuum_sdk.map.payload_parser import MapPayloadParser

from .cloud import XiaomiCloudAuthError
from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .cloud import XiaomiCloud
    from .coordinator import XiaomiVacuumDataUpdateCoordinator
    from .data import MapCalibration, RenderedMap, XiaomiVacuumConfigEntry

MAP_UPDATE_INTERVAL = timedelta(seconds=60)
MAP_STORAGE_VERSION = 1


class _StoredMap(TypedDict):
    """On-disk shape of the cached map; ``calibration`` arrived after ``png_b64``."""

    png_b64: str
    calibration: NotRequired[MapCalibration]


class XiaomiVacuumMapCoordinator(DataUpdateCoordinator["RenderedMap | None"]):
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
        self._store: Store[_StoredMap] = Store(
            hass,
            MAP_STORAGE_VERSION,
            f"{DOMAIN}.map_{state_coordinator.config_entry.entry_id}",
        )
        # The SDK's default RenderOptions carry this integration's palette,
        # scale and element sizes; only the 12 px breathing border is added
        # on top of the legacy render. The same options feed the calibration
        # so pixel coordinates on the served PNG map back to device millimetres.
        self._render_options = RenderOptions()
        self._renderer = MapRenderer(self._render_options)
        self._decryptor = BlobDecryptor()
        self._parser = MapPayloadParser()

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
        self.async_set_updated_data(
            {"png": png, "calibration": stored.get("calibration")}
        )

    async def _async_update_data(self) -> RenderedMap | None:
        # State is None while the robot has been offline since startup; keep
        # serving whatever we have (possibly the disk-restored PNG).
        state = self._state_coordinator.data
        obj_name = self._extract_obj_name(state.get("map_obj_name")) if state else None
        device = self._cloud.device
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
            rendered = await self.hass.async_add_executor_job(
                self._render_blob, raw, device.model, str(device.device_id)
            )
            if rendered is None:
                LOGGER.debug("Renderer returned no image for obj=%s", obj_name)
                return self.data
            # Marked as seen only after a successful render, so a transient
            # parse/render failure is retried on the next poll instead of the
            # blob being skipped as a duplicate.
            self._last_raw = raw
        except XiaomiCloudAuthError as exception:
            # The stored session expired: prompt reauth (HA dedupes concurrent
            # flows) and keep serving the last rendered map meanwhile.
            LOGGER.warning("Cloud session rejected; starting reauth: %s", exception)
            self.config_entry.async_start_reauth(self.hass)
            return self.data
        except Exception as exception:
            raise UpdateFailed(exception) from exception
        LOGGER.debug("Rendered PNG: %s bytes", len(rendered["png"]))
        stored: _StoredMap = {"png_b64": base64.b64encode(rendered["png"]).decode()}
        if rendered["calibration"] is not None:
            stored["calibration"] = rendered["calibration"]
        await self._store.async_save(stored)
        return rendered

    def _render_blob(
        self, raw: bytes, model: str, device_id: str
    ) -> RenderedMap | None:
        """
        Decrypt, parse and render the map blob (CPU-bound, runs in the executor).

        The blob is parsed once for the calibration and again inside the SDK
        renderer, which only exposes finished PNG bytes; both steps share the
        same options so the calibration describes the served image exactly.
        """
        try:
            map_data = self._parser.parse(
                self._decryptor.decrypt(raw, model, device_id)
            )
            png = self._renderer.render(raw, model=model, device_id=device_id)
        except MapParseError as exception:
            # The device published a payload without a drawable map (e.g. a
            # fresh map still being built) — keep serving the previous image.
            LOGGER.debug("Map payload not drawable: %s", exception)
            return None
        calibration: MapCalibration = {
            "origin_x": map_data.origin_x,
            "origin_y": map_data.origin_y,
            "resolution": map_data.resolution,
            "width": map_data.width,
            "height": map_data.height,
            "scale": self._render_options.scale,
            "border": self._render_options.border,
        }
        return {"png": png, "calibration": calibration}

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
