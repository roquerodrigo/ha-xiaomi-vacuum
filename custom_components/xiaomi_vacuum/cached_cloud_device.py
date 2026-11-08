"""Cloud-resolved device snapshot persisted in entry.data to skip the lookup."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .cloud import XiaomiDeviceInfo

if TYPE_CHECKING:
    from .data import JsonObject, JsonValue


def _str_or_none(value: JsonValue | None) -> str | None:
    """Coerce a stored JSON value to a string, treating anything else as absent."""
    return value if isinstance(value, str) else None


class CachedCloudDevice:
    """
    Persists the cloud device lookup so setup does not wait on the cloud.

    Finding the vacuum in the account walks every home through the cloud API,
    yet its result (device id, model, region) never changes for an entry.
    The miIO token is not stored again: the entry already holds it.
    """

    @staticmethod
    def to_stored(device: XiaomiDeviceInfo) -> JsonObject:
        """Serialize a resolved device into a JSON-safe dict, without its token."""
        return {
            "device_id": device.device_id,
            "name": device.name,
            "model": device.model,
            "country": device.country,
            "local_ip": device.local_ip,
            "mac": device.mac,
        }

    @staticmethod
    def from_stored(
        stored: JsonValue | None, token: str, country: str
    ) -> XiaomiDeviceInfo | None:
        """
        Rehydrate the stored device, or None when it is unusable.

        A snapshot from another cloud region (the entry was reconfigured since)
        or with a missing field is discarded so setup resolves the device again.
        """
        if not isinstance(stored, dict):
            return None
        device_id = _str_or_none(stored.get("device_id"))
        name = _str_or_none(stored.get("name"))
        model = _str_or_none(stored.get("model"))
        if not (device_id and name is not None and model):
            return None
        if stored.get("country") != country:
            return None
        return XiaomiDeviceInfo(
            device_id=device_id,
            name=name,
            model=model,
            token=token,
            country=country,
            local_ip=_str_or_none(stored.get("local_ip")),
            mac=_str_or_none(stored.get("mac")),
        )
