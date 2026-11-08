from __future__ import annotations

import pytest

from custom_components.xiaomi_vacuum.cached_cloud_device import CachedCloudDevice
from custom_components.xiaomi_vacuum.cloud import XiaomiDeviceInfo

TOKEN = "0" * 32

DEVICE = XiaomiDeviceInfo(
    device_id="1154085352",
    name="X20 Max",
    model="xiaomi.vacuum.d109gl",
    token=TOKEN,
    country="de",
    local_ip="192.168.1.50",
    mac="AA:BB:CC:DD:EE:FF",
)


def test_to_stored_leaves_the_token_out():
    stored = CachedCloudDevice.to_stored(DEVICE)
    assert stored == {
        "device_id": "1154085352",
        "name": "X20 Max",
        "model": "xiaomi.vacuum.d109gl",
        "country": "de",
        "local_ip": "192.168.1.50",
        "mac": "AA:BB:CC:DD:EE:FF",
    }


def test_round_trip_restores_the_device_with_the_entry_token():
    stored = CachedCloudDevice.to_stored(DEVICE)
    assert CachedCloudDevice.from_stored(stored, TOKEN, "de") == DEVICE


def test_optional_fields_may_be_absent():
    stored = {
        "device_id": "1",
        "name": "",
        "model": "xiaomi.vacuum.b108gl",
        "country": "us",
        "local_ip": 7,
    }
    restored = CachedCloudDevice.from_stored(stored, TOKEN, "us")
    assert restored == XiaomiDeviceInfo("1", "", "xiaomi.vacuum.b108gl", TOKEN, "us")


@pytest.mark.parametrize("stored", [None, "garbage", ["list"]])
def test_non_object_is_discarded(stored):
    assert CachedCloudDevice.from_stored(stored, TOKEN, "de") is None


@pytest.mark.parametrize("missing", ["device_id", "name", "model"])
def test_missing_required_field_is_discarded(missing):
    stored = CachedCloudDevice.to_stored(DEVICE)
    del stored[missing]
    assert CachedCloudDevice.from_stored(stored, TOKEN, "de") is None


def test_snapshot_from_another_region_is_discarded():
    stored = CachedCloudDevice.to_stored(DEVICE)
    assert CachedCloudDevice.from_stored(stored, TOKEN, "us") is None
