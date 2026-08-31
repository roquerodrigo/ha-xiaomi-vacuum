from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.xiaomi_vacuum.cached_device_info import CachedDeviceInfo
from custom_components.xiaomi_vacuum.spec import DEFAULT_MODEL


def test_to_stored_then_from_stored_roundtrip():
    info = MagicMock()
    info.model = "xiaomi.vacuum.d109gl"
    info.mac_address = "AA:BB:CC:DD:EE:FF"
    info.firmware_version = "1.0.0"
    info.hardware_version = "rev1"

    cached = CachedDeviceInfo.from_stored(CachedDeviceInfo.to_stored(info))
    assert cached.model == "xiaomi.vacuum.d109gl"
    assert cached.mac_address == "AA:BB:CC:DD:EE:FF"
    assert cached.firmware_version == "1.0.0"
    assert cached.hardware_version == "rev1"


def test_from_stored_falls_back_on_missing_or_invalid_fields():
    cached = CachedDeviceInfo.from_stored({"mac_address": 42})
    assert cached.model == DEFAULT_MODEL
    assert cached.mac_address is None
    assert cached.firmware_version is None
    assert cached.hardware_version is None
