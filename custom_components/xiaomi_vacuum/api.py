"""Local MIoT client for xiaomi_vacuum."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any

from miio import DeviceException, MiotDevice

from .const import (
    ACTION_IDENTIFY,
    ACTION_PAUSE_SWEEPING,
    ACTION_RETURN_HOME,
    ACTION_START_DUST_ARREST,
    ACTION_START_ROOM_SWEEP,
    ACTION_START_SWEEP,
    ACTION_STOP_SWEEPING,
    FAN_SPEEDS,
    LOGGER,
    PROPERTY_MAPPING,
    SWEEP_MOP_TYPES,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class XiaomiVacuumApiClientError(Exception):
    """General API error."""


class XiaomiVacuumApiClientCommunicationError(XiaomiVacuumApiClientError):
    """Communication error (offline, timeout, invalid token)."""


class XiaomiVacuumApiClient:
    """Local MIoT client wrapping python-miio's MiotDevice."""

    def __init__(self, hass: HomeAssistant, host: str, token: str) -> None:
        """Initialize."""
        self._hass = hass
        self._device = MiotDevice(ip=host, token=token, mapping=PROPERTY_MAPPING)

    async def _run(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Run a sync python-miio call in the executor, normalizing errors."""
        try:
            return await self._hass.async_add_executor_job(
                partial(func, *args, **kwargs)
            )
        except DeviceException as exception:
            msg = f"Device error: {exception}"
            raise XiaomiVacuumApiClientCommunicationError(msg) from exception
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Unexpected error: {exception}"
            raise XiaomiVacuumApiClientError(msg) from exception

    async def async_get_info(self) -> Any:
        """Handshake — returns python-miio DeviceInfo (model, mac, fw)."""
        return await self._run(self._device.info)

    async def async_get_state(self) -> dict[str, Any]:
        """Read all mapped properties (indexed by siid+piid; d109gl reuses did)."""
        rows = await self._run(self._device.get_properties_for_mapping)
        LOGGER.debug("Raw MIoT rows: %s", rows)
        by_key = {
            (r["siid"], r["piid"]): r["value"] for r in rows if r.get("code") == 0
        }
        parsed = {
            name: by_key.get((p["siid"], p["piid"]))
            for name, p in PROPERTY_MAPPING.items()
        }
        LOGGER.debug("Parsed state: %s", parsed)
        return parsed

    async def async_start(self) -> None:
        """Start sweeping."""
        await self._run(
            self._device.call_action_by,
            ACTION_START_SWEEP["siid"],
            ACTION_START_SWEEP["aiid"],
        )

    async def async_pause(self) -> None:
        """Pause current job."""
        await self._run(
            self._device.call_action_by,
            ACTION_PAUSE_SWEEPING["siid"],
            ACTION_PAUSE_SWEEPING["aiid"],
        )

    async def async_stop(self) -> None:
        """Stop current job."""
        await self._run(
            self._device.call_action_by,
            ACTION_STOP_SWEEPING["siid"],
            ACTION_STOP_SWEEPING["aiid"],
        )

    async def async_return_home(self) -> None:
        """Stop and return to dock."""
        await self._run(
            self._device.call_action_by,
            ACTION_RETURN_HOME["siid"],
            ACTION_RETURN_HOME["aiid"],
        )

    async def async_locate(self) -> None:
        """Identify (beep + light)."""
        await self._run(
            self._device.call_action_by,
            ACTION_IDENTIFY["siid"],
            ACTION_IDENTIFY["aiid"],
        )

    async def async_start_dust_arrest(self) -> None:
        """Trigger dock to empty the vacuum's dust bin."""
        await self._run(
            self._device.call_action_by,
            ACTION_START_DUST_ARREST["siid"],
            ACTION_START_DUST_ARREST["aiid"],
        )

    async def async_set_fan_speed(self, fan_speed: str) -> None:
        """Set fan speed by label (Silent/Basic/Strong/Full Speed)."""
        if fan_speed not in FAN_SPEEDS:
            msg = f"Unknown fan speed: {fan_speed}"
            raise XiaomiVacuumApiClientError(msg)
        prop = PROPERTY_MAPPING["fan_speed"]
        await self._run(
            self._device.set_property_by,
            prop["siid"],
            prop["piid"],
            FAN_SPEEDS[fan_speed],
        )

    async def async_set_sweep_mop_type(self, mode: str) -> None:
        """Set sweep/mop mode (sweep / mop / sweep_mop / sweep_before_mopping)."""
        if mode not in SWEEP_MOP_TYPES:
            msg = f"Unknown sweep_mop_type: {mode}"
            raise XiaomiVacuumApiClientError(msg)
        await self.async_set_property("sweep_mop_type", SWEEP_MOP_TYPES[mode])

    async def async_set_property(self, name: str, value: int) -> None:
        """Set a MIoT property by mapping name (raw integer value)."""
        if name not in PROPERTY_MAPPING:
            msg = f"Unknown property: {name}"
            raise XiaomiVacuumApiClientError(msg)
        prop = PROPERTY_MAPPING[name]
        await self._run(self._device.set_property_by, prop["siid"], prop["piid"], value)

    async def async_clean_segments(self, segment_ids: list[str]) -> None:
        """Start cleaning specific rooms by their MIoT room IDs."""
        payload = [
            {
                "piid": ACTION_START_ROOM_SWEEP["in_piid"],
                "value": ",".join(str(r) for r in segment_ids),
            }
        ]
        LOGGER.debug("Calling start-vacuum-room-sweep with payload: %s", payload)
        await self._run(
            self._device.call_action_by,
            ACTION_START_ROOM_SWEEP["siid"],
            ACTION_START_ROOM_SWEEP["aiid"],
            payload,
        )
