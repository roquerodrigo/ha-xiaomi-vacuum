"""Map image entity for xiaomi_vacuum (cloud-backed)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from homeassistant.components.image import ImageEntity

from ..entity import XiaomiVacuumEntity  # noqa: TID252

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from ..coordinator import XiaomiVacuumDataUpdateCoordinator  # noqa: TID252
    from ..map_coordinator import XiaomiVacuumMapCoordinator  # noqa: TID252


class XiaomiVacuumMap(XiaomiVacuumEntity, ImageEntity):
    """Renders the vacuum map produced by XiaomiVacuumMapCoordinator."""

    _attr_translation_key = "map"
    _attr_content_type = "image/png"

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
        png = self._map_coordinator.data
        if not png or png == self._last_image:
            return
        self._last_image = png
        self._attr_image_last_updated = datetime.now(UTC)
        self.async_write_ha_state()

    async def async_image(self) -> bytes | None:
        """Serve the freshest rendered PNG, falling back to the last known one."""
        png = self._map_coordinator.data
        if png is not None:
            self._last_image = png
        return self._last_image
