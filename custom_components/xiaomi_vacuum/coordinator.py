"""DataUpdateCoordinator for xiaomi_vacuum."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import XiaomiVacuumApiClientError
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


def _live_fault_code_ids(fault_ids_raw: str | None) -> int | None:
    """
    Return the current active fault code from the X20 Max `Fault Ids` property.

    `Fault Ids` (siid 2/piid 66) is the live fault state, shaped like
    ``{"ts": ..., "fault": [<codes>]}`` where ``[0]`` means no active fault. The
    `Device Fault` property (piid 3) is not used — it latches the last code and
    never resets. Returns None when `Fault Ids` is missing or unparseable.
    """
    if not fault_ids_raw:
        return None
    try:
        ids = json.loads(fault_ids_raw).get("fault") or []
    except ValueError, TypeError, AttributeError:
        return None
    active = [code for code in ids if code]
    return active[0] if active else 0


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

    @property
    def spec(self) -> ModelSpec:
        """The active model's MIoT spec."""
        return self.config_entry.runtime_data.spec

    async def _async_update_data(self) -> VacuumState:
        """Fetch all mapped properties from the device."""
        try:
            data = await self.config_entry.runtime_data.client.async_get_state()
        except XiaomiVacuumApiClientError as exception:
            # Raised on the first failure: the robot being powered off is a
            # normal scenario worth surfacing in Settings → Repairs.
            async_raise_cannot_connect(self.hass, self.config_entry)
            raise UpdateFailed(exception) from exception
        async_clear_cannot_connect(self.hass, self.config_entry)
        data["fault"] = self._derive_fault(data)
        await self._enrich_fault_text(data)
        return data

    def _derive_fault(self, data: VacuumState) -> int | None:
        """Extract the live fault code using the model's fault representation."""
        if self.spec.fault_kind == "simple":
            # S20+: a plain uint32 fault property, already an int (0 == healthy).
            value = data.get("fault")
            return int(value) if isinstance(value, int) else None
        # X20 Max: a JSON fault-ids list.
        return _live_fault_code_ids(data.get("fault_ids"))

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
