"""Exception family for the Xiaomi cloud client."""

from __future__ import annotations


class XiaomiCloudError(Exception):
    """Generic cloud error."""


class XiaomiCloudAuthError(XiaomiCloudError):
    """Authentication failed (login expired, QR not scanned, etc.)."""
