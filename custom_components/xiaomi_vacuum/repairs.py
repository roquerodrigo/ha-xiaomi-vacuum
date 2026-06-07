"""Repair issues raised when the vacuum cannot be reached."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers import issue_registry as ir

from .const import CONF_HOST, DOMAIN, ISSUE_CANNOT_CONNECT

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import XiaomiVacuumConfigEntry


def _issue_id(entry: XiaomiVacuumConfigEntry) -> str:
    """Return the per-entry issue id for the cannot_connect repair."""
    return f"{ISSUE_CANNOT_CONNECT}_{entry.entry_id}"


def async_raise_cannot_connect(
    hass: HomeAssistant, entry: XiaomiVacuumConfigEntry
) -> None:
    """Create the cannot_connect repair issue for this entry (idempotent)."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        _issue_id(entry),
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_CANNOT_CONNECT,
        translation_placeholders={
            "name": entry.title,
            "host": entry.data[CONF_HOST],
        },
    )


def async_clear_cannot_connect(
    hass: HomeAssistant, entry: XiaomiVacuumConfigEntry
) -> None:
    """Delete the cannot_connect repair issue once the device is reachable."""
    ir.async_delete_issue(hass, DOMAIN, _issue_id(entry))
