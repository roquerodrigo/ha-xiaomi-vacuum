from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.xiaomi_vacuum.entity import XiaomiVacuumEntity


def _coord(
    model="xiaomi.vacuum.d109gl",
    name=None,
    host="1.2.3.4",
    mac="AA:BB:CC:DD:EE:FF",
):
    coord = MagicMock()
    coord.config_entry.entry_id = "eid"
    info = MagicMock()
    info.model = model
    info.firmware_version = "1.0.0"
    info.hardware_version = "rev1"
    info.mac_address = mac
    coord.config_entry.runtime_data.info = info
    data = {}
    if name:
        data["name"] = name
    if host:
        data["host"] = host
    coord.config_entry.data = data
    coord.data = {}
    return coord


def test_device_info_uses_custom_name():
    e = XiaomiVacuumEntity(coordinator=_coord(name="Aspirador"))
    assert e._attr_device_info["name"] == "Aspirador"


def test_device_info_falls_back_to_model_name():
    e = XiaomiVacuumEntity(coordinator=_coord())
    assert e._attr_device_info["name"] == "xiaomi.vacuum.d109gl"


def test_device_info_includes_firmware_and_hardware():
    e = XiaomiVacuumEntity(coordinator=_coord())
    assert e._attr_device_info["sw_version"] == "1.0.0"
    assert e._attr_device_info["hw_version"] == "rev1"


def test_device_info_includes_mac_connection():
    from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC

    e = XiaomiVacuumEntity(coordinator=_coord(mac="11:22:33:44:55:66"))
    assert (CONNECTION_NETWORK_MAC, "11:22:33:44:55:66") in e._attr_device_info[
        "connections"
    ]


def test_device_info_no_mac_when_unknown():
    e = XiaomiVacuumEntity(coordinator=_coord(mac=None))
    assert e._attr_device_info["connections"] == set()


def test_patch_state_merges_into_coordinator_data():
    coord = _coord()
    coord.data = {"a": 1, "b": 2}
    e = XiaomiVacuumEntity(coordinator=coord)
    e._patch_state(b=99, c=3)
    coord.async_set_updated_data.assert_called_once_with({"a": 1, "b": 99, "c": 3})
