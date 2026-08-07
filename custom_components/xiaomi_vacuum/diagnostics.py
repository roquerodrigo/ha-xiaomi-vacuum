"""Diagnostics support for xiaomi_vacuum."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict, cast

from homeassistant.components.diagnostics import async_redact_data

from .const import (
    CONF_CLOUD_SERVICE_TOKEN,
    CONF_CLOUD_SSECURITY,
    CONF_CLOUD_USER_ID,
    CONF_TOKEN,
)
from .spec import SUPPORTED_MODELS

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import JsonObject, XiaomiVacuumConfigEntry

TO_REDACT: frozenset[str] = frozenset(
    {
        CONF_TOKEN,
        CONF_CLOUD_SSECURITY,
        CONF_CLOUD_SERVICE_TOKEN,
        CONF_CLOUD_USER_ID,
    },
)


class XiaomiVacuumDiagnosticsEntry(TypedDict):
    """Redacted snapshot of the config entry."""

    title: str
    version: int
    domain: str
    data: JsonObject


class XiaomiVacuumDiagnosticsDevice(TypedDict):
    """Summary of the device resolved at setup."""

    model: str | None
    supported: bool
    firmware_version: str | None
    hardware_version: str | None


class XiaomiVacuumDiagnosticsPayload(TypedDict):
    """Full diagnostics payload for one config entry."""

    entry: XiaomiVacuumDiagnosticsEntry
    device: XiaomiVacuumDiagnosticsDevice
    coordinator_state: JsonObject
    coordinator_last_update_success: bool
    has_cloud_session: bool


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,  # noqa: ARG001 - signature fixed by Home Assistant
    entry: XiaomiVacuumConfigEntry,
) -> XiaomiVacuumDiagnosticsPayload:
    """Return diagnostics for a config entry, with cloud credentials redacted."""
    runtime = entry.runtime_data
    redacted_data = cast(
        "JsonObject",
        async_redact_data(dict(entry.data), set(TO_REDACT)),
    )
    diagnostics_entry: XiaomiVacuumDiagnosticsEntry = {
        "title": entry.title,
        "version": entry.version,
        "domain": entry.domain,
        "data": redacted_data,
    }
    model = getattr(runtime.info, "model", None)
    device: XiaomiVacuumDiagnosticsDevice = {
        "model": model,
        "supported": model in SUPPORTED_MODELS,
        "firmware_version": getattr(runtime.info, "firmware_version", None),
        "hardware_version": getattr(runtime.info, "hardware_version", None),
    }
    coordinator = runtime.coordinator
    # `coordinator.data` is typed non-optional but is still None at runtime
    # when the tolerated offline first refresh failed.
    coordinator_state = (
        cast("JsonObject", dict(coordinator.data)) if coordinator.data else {}
    )
    return {
        "entry": diagnostics_entry,
        "device": device,
        "coordinator_state": coordinator_state,
        "coordinator_last_update_success": coordinator.last_update_success,
        "has_cloud_session": runtime.map_coordinator is not None,
    }
