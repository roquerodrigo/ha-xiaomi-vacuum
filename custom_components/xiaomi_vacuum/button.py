"""Button platform for xiaomi_vacuum."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity

from .entity import XiaomiVacuumEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import XiaomiVacuumDataUpdateCoordinator
    from .data import XiaomiVacuumConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: XiaomiVacuumConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities."""
    async_add_entities([DustArrestButton(coordinator=entry.runtime_data.coordinator)])


class DustArrestButton(XiaomiVacuumEntity, ButtonEntity):
    """Triggers the dock to empty the vacuum's dust bin."""

    _attr_translation_key = "dust_arrest"
    _attr_icon = "mdi:delete-empty"

    def __init__(self, coordinator: XiaomiVacuumDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_dust_arrest"

    async def async_press(self) -> None:
        """Trigger dust arrest on the dock."""
        client = self.coordinator.config_entry.runtime_data.client
        await client.async_start_dust_arrest()
        self._schedule_refresh()
