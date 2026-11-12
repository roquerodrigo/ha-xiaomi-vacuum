"""DataUpdateCoordinator for xiaomi_vacuum."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    XiaomiVacuumApiClientCommunicationError,
    XiaomiVacuumApiClientError,
)
from .cloud import XiaomiCloudAuthError
from .const import DOMAIN, LOGGER
from .data import VacuumState
from .repairs import async_clear_cannot_connect, async_raise_cannot_connect

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .cloud import XiaomiCloud
    from .data import XiaomiVacuumConfigEntry
    from .spec import ModelSpec

UPDATE_INTERVAL = timedelta(seconds=30)


class XiaomiVacuumDataUpdateCoordinator(DataUpdateCoordinator[VacuumState]):
    """Coordinator polling the vacuum's MIoT properties."""

    config_entry: XiaomiVacuumConfigEntry

    def __init__(
        self, hass: HomeAssistant, config_entry: XiaomiVacuumConfigEntry
    ) -> None:
        """Initialize."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
            config_entry=config_entry,
        )
        # Set after the cloud session resolves (see __init__.py); when present,
        # we enrich a non-zero fault code with its localized text.
        self.cloud: XiaomiCloud | None = None
        self.fault_history: list[dict[str, str | int]] | None = None

    @property
    def spec(self) -> ModelSpec:
        """The active model's MIoT spec."""
        return self.config_entry.runtime_data.spec

    async def _async_update_data(self) -> VacuumState:
        """Fetch all mapped properties from the device."""
        try:
            data = await self.config_entry.runtime_data.client.async_get_state()
        except XiaomiVacuumApiClientCommunicationError as exception:
            # Raised on the first failure: the robot being powered off is a
            # normal scenario worth surfacing in Settings → Repairs.
            async_raise_cannot_connect(self.hass, self.config_entry)
            raise UpdateFailed(exception) from exception
        except XiaomiVacuumApiClientError as exception:
            # Not a connectivity problem — fail the update without pointing
            # the user at their network.
            raise UpdateFailed(exception) from exception
        async_clear_cannot_connect(self.hass, self.config_entry)
        data["fault"] = self.spec.live_fault_code(data)
        await self._enrich_fault_text(data)
        return data

    async def _enrich_fault_text(self, data: VacuumState) -> None:
        """Add the localized fault text for a non-zero fault code, if available."""
        fault = data.get("fault")
        if self.cloud is None or not isinstance(fault, int) or fault == 0:
            return
        try:
            text = await self.cloud.async_fault_text(fault)
        except XiaomiCloudAuthError:
            # The stored session expired mid-run: prompt reauth (HA dedupes
            # concurrent flows) but keep the local state update healthy.
            self.config_entry.async_start_reauth(self.hass)
            return
        if text:
            data["fault_text"] = text
