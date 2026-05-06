"""Image platform serving the rendered vacuum map (cloud-backed)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from homeassistant.components.image import ImageEntity

from .entity import XiaomiVacuumEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import XiaomiVacuumDataUpdateCoordinator
    from .data import XiaomiVacuumConfigEntry
    from .map_coordinator import XiaomiVacuumMapCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: XiaomiVacuumConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the map image entity (only when the cloud coordinator is configured)."""
    map_coord = entry.runtime_data.map_coordinator
    if map_coord is None:
        return
    async_add_entities(
        [
            XiaomiVacuumMap(
                hass,
                state_coordinator=entry.runtime_data.coordinator,
                map_coordinator=map_coord,
            )
        ]
    )


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
        self._attr_unique_id = f"{state_coordinator.config_entry.entry_id}_map"
        self._last_image: bytes | None = None
        self._attr_image_last_updated = datetime.now(UTC)

    async def async_added_to_hass(self) -> None:
        """Subscribe to the map coordinator for refresh on new map data."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._map_coordinator.async_add_listener(self._handle_new_map)
        )

    def _handle_new_map(self) -> None:
        png = self._map_coordinator.data
        if not png or png == self._last_image:
            return
        self._last_image = png
        self._attr_image_last_updated = datetime.now(UTC)
        self.async_write_ha_state()

    async def async_image(self) -> bytes | None:
        """Serve the latest rendered PNG bytes."""
        return self._map_coordinator.data
