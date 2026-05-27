"""Device record returned by the Xiaomi cloud."""

from __future__ import annotations

from typing import NamedTuple


class XiaomiDeviceInfo(NamedTuple):
    """A single device discovered in the Xiaomi cloud account."""

    device_id: str
    name: str
    model: str
    token: str
    country: str
    local_ip: str | None = None
    mac: str | None = None
