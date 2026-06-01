"""Dust-arrest button entity for xiaomi_vacuum."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity

from ..entity import XiaomiVacuumEntity  # noqa: TID252


class XiaomiVacuumDustArrestButton(XiaomiVacuumEntity, ButtonEntity):
    """Triggers the dock to empty the vacuum's dust bin."""

    _attr_translation_key = "dust_arrest"
    _attr_icon = "mdi:delete-empty"

    @property
    def unique_id(self) -> str:
        """Return a stable unique id for this entity."""
        return f"{self.coordinator.config_entry.entry_id}_dust_arrest"

    async def async_press(self) -> None:
        """Trigger dust arrest on the dock."""
        client = self.coordinator.config_entry.runtime_data.client
        await client.async_start_dust_arrest()
        self._schedule_refresh()
