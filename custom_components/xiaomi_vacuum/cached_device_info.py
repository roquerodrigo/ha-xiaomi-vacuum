"""Device-info snapshot persisted in entry.data for offline setup."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .const import MODEL

if TYPE_CHECKING:
    from .data import DeviceInfoLike, JsonObject, JsonValue


def _str_or_none(value: JsonValue | None) -> str | None:
    """Coerce a stored JSON value to a string, treating anything else as absent."""
    return value if isinstance(value, str) else None


@dataclass(frozen=True)
class CachedDeviceInfo:
    """
    ``DeviceInfoLike`` rebuilt from ``entry.data`` when the vacuum is offline.

    The live handshake result is serialized with :meth:`to_stored` after every
    successful setup; :meth:`from_stored` rehydrates it so entities can be
    created even when the robot is powered off at Home Assistant startup.
    """

    model: str
    mac_address: str | None
    firmware_version: str | None
    hardware_version: str | None
    raw: JsonObject = field(default_factory=dict)

    @classmethod
    def from_stored(cls, stored: JsonObject) -> CachedDeviceInfo:
        """Rehydrate the snapshot stored under ``CONF_DEVICE_INFO``."""
        return cls(
            model=_str_or_none(stored.get("model")) or MODEL,
            mac_address=_str_or_none(stored.get("mac_address")),
            firmware_version=_str_or_none(stored.get("firmware_version")),
            hardware_version=_str_or_none(stored.get("hardware_version")),
        )

    @staticmethod
    def to_stored(info: DeviceInfoLike) -> JsonObject:
        """Serialize a live handshake result into a JSON-safe dict."""
        return {
            "model": getattr(info, "model", None),
            "mac_address": getattr(info, "mac_address", None),
            "firmware_version": getattr(info, "firmware_version", None),
            "hardware_version": getattr(info, "hardware_version", None),
        }
