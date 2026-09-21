"""Map image entity for xiaomi_vacuum (cloud-backed)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, TypedDict

from homeassistant.components.image import ImageEntity
from xiaomi_vacuum_sdk import CoordinateSystem

from ..entity import XiaomiVacuumEntity  # noqa: TID252

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from ..coordinator import XiaomiVacuumDataUpdateCoordinator  # noqa: TID252
    from ..data import MapCalibration  # noqa: TID252
    from ..map_coordinator import XiaomiVacuumMapCoordinator  # noqa: TID252


class _Point(TypedDict):
    """A 2-D point, in image pixels or device millimetres depending on context."""

    x: int
    y: int


class CalibrationPoint(TypedDict):
    """One pixel ↔ device-coordinate pair, in the Xiaomi Vacuum Map Card's format."""

    vacuum: _Point
    map: _Point


class _MapAttributes(TypedDict):
    """Attributes letting a map card translate clicks into device coordinates."""

    calibration_points: list[CalibrationPoint] | None
    calibration: MapCalibration | None


class XiaomiVacuumMap(XiaomiVacuumEntity, ImageEntity):
    """Renders the vacuum map produced by XiaomiVacuumMapCoordinator."""

    _attr_translation_key = "map"
    _attr_content_type = "image/png"
    # Static geometry of the served PNG, not history worth recording.
    _unrecorded_attributes = frozenset({"calibration", "calibration_points"})

    def __init__(
        self,
        hass: HomeAssistant,
        state_coordinator: XiaomiVacuumDataUpdateCoordinator,
        map_coordinator: XiaomiVacuumMapCoordinator,
    ) -> None:
        """Initialize."""
        XiaomiVacuumEntity.__init__(self, state_coordinator)
        ImageEntity.__init__(self, hass)
        self._map_coordinator = map_coordinator
        self._last_image: bytes | None = None
        self._last_calibration: MapCalibration | None = None
        self._attr_image_last_updated = datetime.now(UTC)

    @property
    def unique_id(self) -> str:
        """Return a stable unique id for this entity."""
        return f"{self.coordinator.config_entry.entry_id}_map"

    @property
    def available(self) -> bool:
        """
        Available whenever a map image exists, even if the robot is offline.

        Decoupled from the state coordinator on purpose: an unavailable image
        entity makes the frontend request the map with ``token=undefined``,
        which Home Assistant logs as an invalid-authentication attempt.
        """
        return self._map_coordinator.data is not None or self._last_image is not None

    @property
    def extra_state_attributes(self) -> _MapAttributes:
        """Expose the pixel ↔ millimetre calibration of the served PNG."""
        calibration = self._last_calibration
        return {
            "calibration_points": (
                calibration_points(calibration) if calibration is not None else None
            ),
            "calibration": calibration,
        }

    async def async_added_to_hass(self) -> None:
        """Subscribe to the map coordinator for refresh on new map data."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._map_coordinator.async_add_listener(self._handle_new_map)
        )
        # Surface a disk-restored map immediately after a restart.
        if self._map_coordinator.data is not None:
            self._handle_new_map()

    def _handle_new_map(self) -> None:
        rendered = self._map_coordinator.data
        # The calibration is compared too: a cache written before calibration
        # existed restores it as None, and the first poll can re-render the
        # very same PNG — comparing only bytes would drop the calibration
        # until the map itself next changes, which can take hours docked.
        if rendered is None or (
            rendered["png"] == self._last_image
            and rendered["calibration"] == self._last_calibration
        ):
            return
        self._last_image = rendered["png"]
        self._last_calibration = rendered["calibration"]
        self._attr_image_last_updated = datetime.now(UTC)
        self.async_write_ha_state()

    async def async_image(self) -> bytes | None:
        """Serve the freshest rendered PNG, falling back to the last known one."""
        rendered = self._map_coordinator.data
        if rendered is not None:
            self._last_image = rendered["png"]
            self._last_calibration = rendered["calibration"]
        return self._last_image


def calibration_points(calibration: MapCalibration) -> list[CalibrationPoint]:
    """
    Three pixel ↔ millimetre pairs describing the served PNG.

    The projection is the SDK's own ``CoordinateSystem``, rebuilt from the
    stored calibration so the pairs stay the exact inverse of what the
    renderer drew. The pairs are the floor image's top-left, top-right and
    bottom-left corners, which is the three-point form the Xiaomi Vacuum Map
    Card accepts as a ``calibration_source``.
    """
    coordinates = CoordinateSystem(
        origin_x=calibration["origin_x"],
        origin_y=calibration["origin_y"],
        resolution=calibration["resolution"],
        grid_height=calibration["height"],
        scale=calibration["scale"],
        offset=calibration["border"],
    )
    scale = calibration["scale"]
    border = calibration["border"]
    floor_width = calibration["width"] * scale
    floor_height = calibration["height"] * scale
    return [
        _calibration_point(coordinates, border, border),
        _calibration_point(coordinates, border + floor_width, border),
        _calibration_point(coordinates, border, border + floor_height),
    ]


def _calibration_point(
    coordinates: CoordinateSystem, pixel_x: float, pixel_y: float
) -> CalibrationPoint:
    """Project one PNG pixel back onto the device's millimetre frame."""
    point = coordinates.to_device(pixel_x, pixel_y)
    return {
        "map": {"x": round(pixel_x), "y": round(pixel_y)},
        "vacuum": {"x": round(point.x), "y": round(point.y)},
    }
