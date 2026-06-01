from __future__ import annotations

# Imported at runtime (not under TYPE_CHECKING) on purpose: the production code
# only references these TypedDicts under TYPE_CHECKING, so this is the only place
# that executes their class bodies for coverage.
from custom_components.xiaomi_vacuum.cloud import responses  # noqa: TC001


def test_qr_init_shape():
    init: responses.QrInit = {"qr": "https://q", "lp": "https://lp", "timeout": 120}
    assert init["qr"] == "https://q"
    assert init["lp"] == "https://lp"
    assert init["timeout"] == 120


def test_qr_poll_shape():
    poll: responses.QrPoll = {
        "ssecurity": "S",
        "userId": 42,
        "location": "https://loc",
    }
    assert poll["ssecurity"] == "S"
    assert poll["userId"] == 42
    assert poll["location"] == "https://loc"


def test_home_entry_and_homes_result_shape():
    home: responses.HomeEntry = {"id": 1, "uid": 2}
    result: responses.HomesResult = {
        "homelist": [home],
        "share_home_list": [],
    }
    assert result["homelist"][0]["id"] == 1
    assert result["share_home_list"] == []


def test_device_entry_and_devices_result_shape():
    device: responses.DeviceEntry = {
        "did": "d",
        "name": "Vacuum",
        "model": "xiaomi.vacuum.d109gl",
        "token": "abc",
        "localip": "192.168.1.5",
        "local_ip": None,
        "mac": "AA:BB:CC:DD:EE:FF",
    }
    result: responses.DevicesResult = {"device_info": [device]}
    assert result["device_info"][0]["did"] == "d"
    assert result["device_info"][0]["model"] == "xiaomi.vacuum.d109gl"


def test_map_url_result_shape():
    result: responses.MapUrlResult = {"url": "https://x"}
    assert result["url"] == "https://x"


def test_fault_message_chain_shape():
    body: responses.FaultBody = {"value": [210009], "extra": []}
    params: responses.FaultParams = {"body": body}
    message: responses.FaultMessage = {
        "title": "Cannot return to dock",
        "params": params,
    }
    result: responses.FaultResult = {"messages": [message]}
    parsed = result["messages"][0]
    assert parsed["title"] == "Cannot return to dock"
    assert parsed["params"]["body"]["value"] == [210009]
