"""Repair issues raised when the vacuum cannot be reached."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers import issue_registry as ir

from .const import CONF_HOST, DOMAIN, ISSUE_CANNOT_CONNECT, ISSUE_UNSUPPORTED_MODEL

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import XiaomiVacuumConfigEntry


def _issue_id(entry: XiaomiVacuumConfigEntry) -> str:
    """Return the per-entry issue id for the cannot_connect repair."""
    return f"{ISSUE_CANNOT_CONNECT}_{entry.entry_id}"


def _unsupported_issue_id(entry: XiaomiVacuumConfigEntry) -> str:
    """Return the per-entry issue id for the unsupported_model repair."""
    return f"{ISSUE_UNSUPPORTED_MODEL}_{entry.entry_id}"


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


def async_raise_unsupported_model(
    hass: HomeAssistant, entry: XiaomiVacuumConfigEntry, model: str
) -> None:
    """
    Create the unsupported_model repair issue (idempotent).

    The integration falls back to a default spec for an unknown model so local
    control keeps working, but several entities may be wrong (status codes,
    PIIDs, capabilities). Surfacing a repair tells the user to file an issue.
    """
    ir.async_create_issue(
        hass,
        DOMAIN,
        _unsupported_issue_id(entry),
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_UNSUPPORTED_MODEL,
        translation_placeholders={"name": entry.title, "model": model},
    )


def async_clear_unsupported_model(
    hass: HomeAssistant, entry: XiaomiVacuumConfigEntry
) -> None:
    """Delete the unsupported_model repair issue when the model becomes known."""
    ir.async_delete_issue(hass, DOMAIN, _unsupported_issue_id(entry))
