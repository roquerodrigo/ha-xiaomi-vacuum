"""Exception family for the local MIoT API client."""

from __future__ import annotations


class XiaomiVacuumApiClientError(Exception):
    """General API error."""


class XiaomiVacuumApiClientCommunicationError(XiaomiVacuumApiClientError):
    """Communication error (offline, timeout, invalid token)."""
