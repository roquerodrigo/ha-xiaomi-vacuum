"""Error raised when a room clean cannot be started."""

from __future__ import annotations


class RoomCleaningError(Exception):
    """The requested rooms cannot be cleaned with what the device reports."""
