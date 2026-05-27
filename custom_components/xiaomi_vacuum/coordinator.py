"""DataUpdateCoordinator for xiaomi_vacuum."""

from __future__ import annotations

import json
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


def _live_fault_code(fault_ids_raw: str | None) -> int | None:
    """
    Return the current active fault code from the `Fault Ids` property.

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
        data["fault"] = _live_fault_code(data.get("fault_ids"))
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
