"""DataUpdateCoordinator for xiaomi_vacuum."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import XiaomiVacuumApiClientError
from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .cloud import XiaomiCloud
    from .data import XiaomiVacuumConfigEntry

UPDATE_INTERVAL = timedelta(seconds=30)


class XiaomiVacuumDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator polling the vacuum's MIoT properties."""

    config_entry: XiaomiVacuumConfigEntry

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        # Set after the cloud session resolves (see __init__.py); when present,
        # we enrich a non-zero fault code with its localized text.
        self.cloud: XiaomiCloud | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch all mapped properties from the device."""
        try:
            data = await self.config_entry.runtime_data.client.async_get_state()
        except XiaomiVacuumApiClientError as exception:
            raise UpdateFailed(exception) from exception
        await self._enrich_fault_text(data)
        return data

    async def _enrich_fault_text(self, data: dict[str, Any]) -> None:
        """Add the localized fault text for a non-zero fault code, if available."""
        fault = data.get("fault")
        if self.cloud is None or not isinstance(fault, int) or fault == 0:
            return
        text = await self.cloud.async_fault_text(fault)
        if text:
            data["fault_text"] = text
