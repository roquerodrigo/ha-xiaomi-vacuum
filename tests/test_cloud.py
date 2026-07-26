from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.xiaomi_vacuum.cloud import (
    XiaomiCloud,
    XiaomiCloudError,
    XiaomiDeviceInfo,
    _XiaomiCloudConnector,
)


def _resp(status=200, text="", cookies=None, content=b""):
    r = MagicMock()
    r.status_code = status
    r.text = text
    r.content = content
    r.cookies = cookies or {}
    return r


def _connector_with_session(session_mock):
    c = _XiaomiCloudConnector()
    c._session = session_mock
    return c


def _aio_resp(status=200, text="", token_cookie=None):
    """Mock an aiohttp ClientResponse usable as `async with session.get(...) as r`."""
    r = MagicMock()
    r.status = status
    r.text = AsyncMock(return_value=text)
    if token_cookie is None:
        r.cookies.get = MagicMock(return_value=None)
    else:
        cookie = MagicMock()
        cookie.value = token_cookie
        r.cookies.get = MagicMock(return_value=cookie)
    r.__aenter__ = AsyncMock(return_value=r)
    r.__aexit__ = AsyncMock(return_value=None)
    return r


def _patch_aiohttp(*responses):
    """Patch async_get_clientsession to a session whose .get yields `responses`."""
    session = MagicMock()
    session.get = MagicMock(side_effect=list(responses))
    return patch(
        "custom_components.xiaomi_vacuum.cloud.client.async_get_clientsession",
        return_value=session,
    )


def test_api_url_cn_no_prefix():
    assert _XiaomiCloudConnector._api_url("cn") == "https://api.io.mi.com/app"


def test_api_url_other_country():
    assert _XiaomiCloudConnector._api_url("de") == "https://de.api.io.mi.com/app"


def test_to_json_strips_marker():
    raw = '&&&START&&&{"a":1}'
    assert _XiaomiCloudConnector._to_json(raw) == {"a": 1}


def test_rc4_roundtrip():
    import base64

    pwd = base64.b64encode(b"\x00" * 32).decode()
    enc = _XiaomiCloudConnector._encrypt_rc4(pwd, "hello")
    dec = _XiaomiCloudConnector._decrypt_rc4(pwd, enc)
    assert dec.decode() == "hello"


def test_signed_nonce_deterministic():
    import base64

    c = _XiaomiCloudConnector()
    c._ssecurity = base64.b64encode(b"\x01" * 32).decode()
    nonce = base64.b64encode(b"\x02" * 12).decode()
    assert c._signed_nonce(nonce) == c._signed_nonce(nonce)


def test_start_qr_login_returns_image_lp_url_and_timeout():
    sess = MagicMock()
    sess.get.side_effect = [
        _resp(text='&&&START&&&{"qr":"https://q","lp":"https://lp","timeout":120}'),
        _resp(content=b"PNG_BYTES"),
    ]
    c = _connector_with_session(sess)
    qr, lp, timeout = c.start_qr_login()
    assert qr == b"PNG_BYTES"
    assert lp == "https://lp"
    assert timeout == 120


def test_poll_qr_login_success_returns_true_and_sets_tokens():
    sess = MagicMock()
    body = '&&&START&&&{"ssecurity":"S","userId":42,"location":"https://loc"}'
    cookies = MagicMock()
    cookies.get = MagicMock(return_value="TOK")
    sess.get.side_effect = [
        _resp(text=body),  # long-polling response
        _resp(cookies=cookies),  # /location → serviceToken cookie
    ]
    c = _connector_with_session(sess)
    assert c.poll_qr_login("https://lp", timeout=10) is True
    assert c._ssecurity == "S"
    assert c._user_id == "42"
    assert c._service_token == "TOK"


def test_poll_qr_login_returns_false_when_service_token_missing():
    sess = MagicMock()
    body = '&&&START&&&{"ssecurity":"S","userId":42,"location":"https://loc"}'
    cookies = MagicMock()
    cookies.get = MagicMock(return_value=None)
    sess.get.side_effect = [
        _resp(text=body),
        _resp(cookies=cookies),
    ]
    c = _connector_with_session(sess)
    assert c.poll_qr_login("https://lp", timeout=10) is False


def test_poll_qr_login_returns_false_on_timeout(monkeypatch):
    sess = MagicMock()
    sess.get.return_value = _resp(text='&&&START&&&{"waiting":true}')
    c = _connector_with_session(sess)
    # 0s timeout → never enters loop → returns False
    assert c.poll_qr_login("https://lp", timeout=0) is False


def test_find_device_returns_match():
    c = _XiaomiCloudConnector()
    target = XiaomiDeviceInfo(
        device_id="d",
        name="x",
        model="m",
        token="abc",
        country="cn",
    )
    with patch.object(c, "_iter_devices", return_value=iter([target])):
        result = c.find_device("ABC", "cn")
    assert result is target


def test_find_device_returns_none_when_no_match():
    c = _XiaomiCloudConnector()
    with patch.object(c, "_iter_devices", return_value=iter([])):
        assert c.find_device("nope", "cn") is None


def test_get_device_fault_texts_maps_code_to_title():
    c = _XiaomiCloudConnector()
    response = {
        "result": {
            "messages": [
                {
                    "title": "Não foi possível voltar à base para carregar.",
                    "params": {"body": {"event": "2.3", "value": [210009]}},
                },
                # status notice without a code -> ignored
                {
                    "title": "Limpeza concluída",
                    "params": {"body": {"event": "2.2", "value": []}},
                },
            ]
        }
    }
    with patch.object(c, "_encrypted_call", return_value=response):
        texts = c.get_device_fault_texts("us", "1154085352")
    assert texts == {210009: "Não foi possível voltar à base para carregar."}


def test_get_device_fault_texts_empty_on_no_result():
    c = _XiaomiCloudConnector()
    with patch.object(c, "_encrypted_call", return_value=None):
        assert c.get_device_fault_texts("us", "did") == {}


def test_get_map_url_pro_endpoint_succeeds_when_first_fails():
    c = _XiaomiCloudConnector()
    responses = [
        {"code": -6, "result": None},
        {"code": 0, "result": {"url": "https://x"}},
    ]
    with patch.object(c, "_encrypted_call", side_effect=responses):
        assert c.get_map_url("us", "obj") == "https://x"


def test_get_map_url_returns_none_when_both_endpoints_fail():
    c = _XiaomiCloudConnector()
    with patch.object(c, "_encrypted_call", return_value={"code": -6, "result": None}):
        assert c.get_map_url("us", "obj") is None


def test_get_map_bytes_success():
    sess = MagicMock()
    sess.get.return_value = _resp(content=b"BIN")
    c = _connector_with_session(sess)
    assert c.get_map_bytes("https://x") == b"BIN"


def test_get_map_bytes_non_200_returns_none():
    sess = MagicMock()
    sess.get.return_value = _resp(status=404)
    c = _connector_with_session(sess)
    assert c.get_map_bytes("https://x") is None


async def test_xiaomi_cloud_from_session_skips_login(hass):
    cloud = XiaomiCloud.from_session(hass, "us", "ssec", "tok", "uid")
    assert cloud._logged_in is True
    assert cloud._connector._ssecurity == "ssec"
    assert cloud._connector._service_token == "tok"
    assert cloud._connector._user_id == "uid"


async def test_session_tokens_returns_current_state(hass):
    cloud = XiaomiCloud.from_session(hass, "us", "ssec", "tok", "uid")
    assert cloud.session_tokens() == {
        "ssecurity": "ssec",
        "service_token": "tok",
        "user_id": "uid",
    }


async def test_async_qr_start(hass):
    cloud = XiaomiCloud(hass, "us")
    with patch.object(
        cloud._connector,
        "start_qr_login",
        return_value=(b"PNG", "https://lp", 60),
    ):
        qr, lp, timeout = await cloud.async_qr_start()
    assert qr == b"PNG"
    assert lp == "https://lp"
    assert timeout == 60


async def test_async_poll_qr_login_success(hass):
    cloud = XiaomiCloud(hass, "us")
    body = '&&&START&&&{"ssecurity":"S","userId":42,"location":"https://loc"}'
    with _patch_aiohttp(_aio_resp(text=body), _aio_resp(token_cookie="TOK")):
        assert await cloud._async_poll_qr_login("https://lp", 1) is True
    assert cloud._connector._ssecurity == "S"
    assert cloud._connector._user_id == "42"
    assert cloud._connector._service_token == "TOK"


async def test_async_poll_qr_login_returns_false_on_non_200(hass):
    cloud = XiaomiCloud(hass, "us")
    with _patch_aiohttp(_aio_resp(status=503)):
        assert await cloud._async_poll_qr_login("https://lp", 1) is False


async def test_async_poll_qr_login_returns_false_when_body_missing_ssecurity(hass):
    cloud = XiaomiCloud(hass, "us")
    with _patch_aiohttp(_aio_resp(text='&&&START&&&{"waiting":true}')):
        assert await cloud._async_poll_qr_login("https://lp", 1) is False


async def test_async_poll_qr_login_returns_false_when_service_token_missing(hass):
    cloud = XiaomiCloud(hass, "us")
    body = '&&&START&&&{"ssecurity":"S","userId":42,"location":"https://loc"}'
    with _patch_aiohttp(_aio_resp(text=body), _aio_resp(token_cookie=None)):
        assert await cloud._async_poll_qr_login("https://lp", 1) is False


async def test_async_poll_qr_login_returns_false_on_timeout(hass):

    cloud = XiaomiCloud(hass, "us")
    session = MagicMock()
    session.get = MagicMock(side_effect=TimeoutError())
    with patch(
        "custom_components.xiaomi_vacuum.cloud.client.async_get_clientsession",
        return_value=session,
    ):
        assert await cloud._async_poll_qr_login("https://lp", 1) is False


async def test_async_qr_login_success_sets_logged_in(hass):
    cloud = XiaomiCloud(hass, "us")
    with patch.object(cloud, "_async_poll_qr_login", AsyncMock(return_value=True)):
        await cloud.async_qr_login("https://lp", wait_seconds=1)
    assert cloud._logged_in is True


async def test_async_qr_login_raises_auth_error_on_failure(hass):
    from custom_components.xiaomi_vacuum.cloud import XiaomiCloudAuthError

    cloud = XiaomiCloud(hass, "us")
    with (
        patch.object(cloud, "_async_poll_qr_login", AsyncMock(return_value=False)),
        pytest.raises(XiaomiCloudAuthError, match="not scanned"),
    ):
        await cloud.async_qr_login("https://lp", wait_seconds=1)
    assert cloud._logged_in is False


async def test_async_poll_qr_login_returns_false_when_location_missing(hass):
    cloud = XiaomiCloud(hass, "us")
    body = '&&&START&&&{"ssecurity":"S","userId":42}'
    with _patch_aiohttp(_aio_resp(text=body)):
        assert await cloud._async_poll_qr_login("https://lp", 1) is False
    assert cloud._connector._ssecurity == "S"


async def test_async_poll_qr_login_returns_false_when_token_fetch_non_200(hass):
    cloud = XiaomiCloud(hass, "us")
    body = '&&&START&&&{"ssecurity":"S","userId":42,"location":"https://loc"}'
    with _patch_aiohttp(_aio_resp(text=body), _aio_resp(status=403)):
        assert await cloud._async_poll_qr_login("https://lp", 1) is False


async def test_async_poll_qr_login_returns_false_on_token_fetch_timeout(hass):
    cloud = XiaomiCloud(hass, "us")
    body = '&&&START&&&{"ssecurity":"S","userId":42,"location":"https://loc"}'
    session = MagicMock()
    session.get = MagicMock(side_effect=[_aio_resp(text=body), TimeoutError()])
    with patch(
        "custom_components.xiaomi_vacuum.cloud.client.async_get_clientsession",
        return_value=session,
    ):
        assert await cloud._async_poll_qr_login("https://lp", 1) is False


async def test_async_resolve_device_not_found_raises(hass):
    cloud = XiaomiCloud(hass, "us")
    with (
        patch.object(cloud._connector, "find_device", return_value=None),
        pytest.raises(XiaomiCloudError, match="not found"),
    ):
        await cloud.async_resolve_device("abc")


async def test_async_get_map_bytes_returns_none_when_not_logged_in(hass):
    cloud = XiaomiCloud(hass, "us")
    assert await cloud.async_get_map_bytes("obj") is None


async def test_async_get_map_bytes_success(hass):
    cloud = XiaomiCloud(hass, "us")
    cloud._logged_in = True
    cloud._device = XiaomiDeviceInfo("d", "x", "m", "abc", "us")
    with (
        patch.object(cloud._connector, "get_map_url", return_value="https://x"),
        patch.object(cloud._connector, "get_map_bytes", return_value=b"PNG"),
    ):
        assert await cloud.async_get_map_bytes("obj") == b"PNG"


async def test_async_get_map_bytes_no_url_returns_none(hass):
    cloud = XiaomiCloud(hass, "us")
    cloud._logged_in = True
    cloud._device = XiaomiDeviceInfo("d", "x", "m", "abc", "us")
    with patch.object(cloud._connector, "get_map_url", return_value=None):
        assert await cloud.async_get_map_bytes("obj") is None


def _signed_connector():
    """A connector with a deterministic ssecurity so signing works."""
    import base64

    c = _XiaomiCloudConnector()
    c._ssecurity = base64.b64encode(b"\x07" * 32).decode()
    c._user_id = "42"
    c._service_token = "TOK"
    return c


def test_poll_qr_login_returns_false_on_request_exception():
    import requests

    sess = MagicMock()
    sess.get.side_effect = requests.RequestException("boom")
    c = _connector_with_session(sess)
    assert c.poll_qr_login("https://lp", timeout=10) is False


def test_poll_qr_login_returns_false_on_non_200():
    sess = MagicMock()
    sess.get.return_value = _resp(status=503, text="busy")
    c = _connector_with_session(sess)
    assert c.poll_qr_login("https://lp", timeout=10) is False


def test_poll_qr_login_returns_false_when_no_ssecurity():
    sess = MagicMock()
    sess.get.return_value = _resp(text='&&&START&&&{"waiting":true}')
    c = _connector_with_session(sess)
    assert c.poll_qr_login("https://lp", timeout=10) is False


def test_poll_qr_login_returns_false_when_location_missing():
    sess = MagicMock()
    body = '&&&START&&&{"ssecurity":"S","userId":42}'
    sess.get.return_value = _resp(text=body)
    c = _connector_with_session(sess)
    assert c.poll_qr_login("https://lp", timeout=10) is False
    assert c._ssecurity == "S"
    assert c._user_id == "42"


def test_fetch_service_token_non_200_returns_false():
    sess = MagicMock()
    sess.get.return_value = _resp(status=403)
    c = _connector_with_session(sess)
    assert c._fetch_service_token("https://loc") is False


def test_iter_homes_yields_owned_and_shared():
    c = _XiaomiCloudConnector()
    response = {
        "result": {
            "homelist": [{"id": 1, "uid": 10}],
            "share_home_list": [{"id": 2, "uid": 20}],
        }
    }
    with patch.object(c, "_encrypted_call", return_value=response):
        homes = list(c._iter_homes("us"))
    assert [h["id"] for h in homes] == [1, 2]


def test_iter_homes_empty_when_no_result():
    c = _XiaomiCloudConnector()
    with patch.object(c, "_encrypted_call", return_value=None):
        assert list(c._iter_homes("us")) == []


def test_iter_home_devices_builds_device_info():
    c = _XiaomiCloudConnector()
    response = {
        "result": {
            "device_info": [
                {
                    "did": "d1",
                    "name": "Vacuum",
                    "model": "xiaomi.vacuum.d109gl",
                    "token": "abc",
                    "localip": "192.168.1.7",
                    "mac": "AA:BB:CC:DD:EE:FF",
                }
            ]
        }
    }
    with patch.object(c, "_encrypted_call", return_value=response):
        devices = list(c._iter_home_devices("us", 1, 10))
    assert len(devices) == 1
    assert devices[0].device_id == "d1"
    assert devices[0].local_ip == "192.168.1.7"
    assert devices[0].mac == "AA:BB:CC:DD:EE:FF"


def test_iter_home_devices_falls_back_to_local_ip_key():
    c = _XiaomiCloudConnector()
    response = {
        "result": {
            "device_info": [
                {
                    "did": "d2",
                    "name": "V",
                    "model": "m",
                    "token": "t",
                    "local_ip": "10.0.0.9",
                }
            ]
        }
    }
    with patch.object(c, "_encrypted_call", return_value=response):
        devices = list(c._iter_home_devices("us", 1, 10))
    assert devices[0].local_ip == "10.0.0.9"


def test_iter_home_devices_empty_when_no_result():
    c = _XiaomiCloudConnector()
    with patch.object(c, "_encrypted_call", return_value={"result": None}):
        assert list(c._iter_home_devices("us", 1, 10)) == []


def test_iter_devices_walks_homes_then_devices():
    c = _XiaomiCloudConnector()
    target = XiaomiDeviceInfo("d", "x", "m", "abc", "us")
    with (
        patch.object(c, "_iter_homes", return_value=iter([{"id": 1, "uid": 10}])),
        patch.object(c, "_iter_home_devices", return_value=iter([target])) as ihd,
    ):
        devices = list(c._iter_devices("us"))
    assert devices == [target]
    ihd.assert_called_once_with("us", 1, 10)


def test_get_map_url_skips_empty_response():
    c = _XiaomiCloudConnector()
    with patch.object(c, "_encrypted_call", side_effect=[None, {"result": {}}]):
        assert c.get_map_url("us", "obj") is None


def test_get_device_fault_texts_ignores_unparseable_code():
    c = _XiaomiCloudConnector()
    response = {
        "result": {
            "messages": [
                {
                    "title": "Bad code",
                    "params": {"body": {"value": ["not-an-int"]}},
                }
            ]
        }
    }
    with patch.object(c, "_encrypted_call", return_value=response):
        assert c.get_device_fault_texts("us", "did") == {}


def test_get_device_fault_texts_uses_extra_when_value_missing():
    c = _XiaomiCloudConnector()
    response = {
        "result": {
            "messages": [
                {
                    "title": "Extra fault",
                    "params": {"body": {"extra": [120]}},
                }
            ]
        }
    }
    with patch.object(c, "_encrypted_call", return_value=response):
        assert c.get_device_fault_texts("us", "did") == {120: "Extra fault"}


def test_encrypted_call_signs_and_decrypts_round_trip():
    c = _signed_connector()
    captured = {}

    def fake_post(url, headers, cookies, params, timeout):
        captured["params"] = params
        plaintext = json.dumps({"result": {"ok": True}})
        encrypted = _XiaomiCloudConnector._encrypt_rc4(
            c._signed_nonce(params["_nonce"]), plaintext
        )
        return _resp(text=encrypted)

    c._session = MagicMock()
    c._session.post.side_effect = fake_post
    result = c._encrypted_call("https://api.io.mi.com/app/v2/x", {"data": "{}"})
    assert result == {"result": {"ok": True}}
    assert "signature" in captured["params"]
    assert "_nonce" in captured["params"]
    assert captured["params"]["ssecurity"] == c._ssecurity


def test_encrypted_call_returns_none_on_non_200():
    c = _signed_connector()
    c._session = MagicMock()
    c._session.post.return_value = _resp(status=500)
    assert c._encrypted_call("https://api.io.mi.com/app/v2/x", {"data": "{}"}) is None


def test_signed_nonce_raises_without_ssecurity():
    import base64

    c = _XiaomiCloudConnector()
    c._ssecurity = None
    nonce = base64.b64encode(b"\x02" * 12).decode()
    with pytest.raises(XiaomiCloudError, match="ssecurity not set"):
        c._signed_nonce(nonce)


def test_gen_enc_params_raises_without_ssecurity():
    c = _XiaomiCloudConnector()
    c._ssecurity = None
    with pytest.raises(XiaomiCloudError, match="ssecurity not set"):
        c._gen_enc_params("https://api.io.mi.com/app/v2/x", "POST", "n", "n", {})


def test_gen_nonce_is_base64_decodable():
    import base64

    nonce = _XiaomiCloudConnector._gen_nonce(1_700_000_000_000)
    assert len(base64.b64decode(nonce)) == 12


def test_enc_signature_is_deterministic():
    sig1 = _XiaomiCloudConnector._enc_signature(
        "https://api.io.mi.com/app/v2/x", "POST", "nonce", {"a": "1"}
    )
    sig2 = _XiaomiCloudConnector._enc_signature(
        "https://api.io.mi.com/app/v2/x", "POST", "nonce", {"a": "1"}
    )
    assert sig1 == sig2


async def test_async_list_devices_filters_by_model_prefix(hass):
    cloud = XiaomiCloud(hass, "us")
    vacuum = XiaomiDeviceInfo("d", "x", "xiaomi.vacuum.d109gl", "abc", "us")
    lamp = XiaomiDeviceInfo("l", "lamp", "yeelink.light.1", "def", "us")
    with patch.object(
        cloud._connector, "_iter_devices", return_value=iter([vacuum, lamp])
    ):
        devices = await cloud.async_list_devices(model_prefix="xiaomi.vacuum.")
    assert devices == [vacuum]


async def test_async_list_devices_prefix_matches_b108gl(hass):
    """The X20 (b108gl) must be discoverable by the same `xiaomi.vacuum.` prefix."""
    cloud = XiaomiCloud(hass, "us")
    x20 = XiaomiDeviceInfo("d2", "x20", "xiaomi.vacuum.b108gl", "abc", "us")
    lamp = XiaomiDeviceInfo("l", "lamp", "yeelink.light.1", "def", "us")
    with patch.object(
        cloud._connector, "_iter_devices", return_value=iter([x20, lamp])
    ):
        devices = await cloud.async_list_devices(model_prefix="xiaomi.vacuum.")
    assert devices == [x20]


async def test_async_list_devices_returns_all_without_prefix(hass):
    cloud = XiaomiCloud(hass, "us")
    vacuum = XiaomiDeviceInfo("d", "x", "xiaomi.vacuum.d109gl", "abc", "us")
    lamp = XiaomiDeviceInfo("l", "lamp", "yeelink.light.1", "def", "us")
    with patch.object(
        cloud._connector, "_iter_devices", return_value=iter([vacuum, lamp])
    ):
        devices = await cloud.async_list_devices()
    assert devices == [vacuum, lamp]


async def test_async_resolve_device_caches_device(hass):
    cloud = XiaomiCloud(hass, "us")
    device = XiaomiDeviceInfo("d", "x", "m", "abc", "us")
    with patch.object(cloud._connector, "find_device", return_value=device):
        resolved = await cloud.async_resolve_device("abc")
    assert resolved is device
    assert cloud._device is device


async def test_async_fault_text_returns_none_when_not_logged_in(hass):
    cloud = XiaomiCloud(hass, "us")
    assert await cloud.async_fault_text(210009) is None


async def test_async_fault_text_returns_none_for_zero_code(hass):
    cloud = XiaomiCloud(hass, "us")
    cloud._logged_in = True
    cloud._device = XiaomiDeviceInfo("d", "x", "m", "abc", "us")
    assert await cloud.async_fault_text(0) is None


async def test_async_fault_text_queries_once_and_caches(hass):
    cloud = XiaomiCloud(hass, "us")
    cloud._logged_in = True
    cloud._device = XiaomiDeviceInfo("d", "x", "m", "abc", "us")
    with patch.object(
        cloud._connector,
        "get_device_fault_texts",
        return_value={210009: "Cannot return"},
    ) as fetch:
        first = await cloud.async_fault_text(210009)
        second = await cloud.async_fault_text(210009)
    assert first == "Cannot return"
    assert second == "Cannot return"
    fetch.assert_called_once()


async def test_async_fault_text_unmatched_code_not_requeried(hass):
    cloud = XiaomiCloud(hass, "us")
    cloud._logged_in = True
    cloud._device = XiaomiDeviceInfo("d", "x", "m", "abc", "us")
    with patch.object(
        cloud._connector, "get_device_fault_texts", return_value={}
    ) as fetch:
        assert await cloud.async_fault_text(999) is None
        assert await cloud.async_fault_text(999) is None
    fetch.assert_called_once()


async def test_async_fault_text_returns_none_on_connector_error(hass):
    cloud = XiaomiCloud(hass, "us")
    cloud._logged_in = True
    cloud._device = XiaomiDeviceInfo("d", "x", "m", "abc", "us")
    with patch.object(
        cloud._connector,
        "get_device_fault_texts",
        side_effect=XiaomiCloudError("boom"),
    ):
        assert await cloud.async_fault_text(210009) is None


def test_call_action_targets_mdotspec_endpoint():
    """The cloud action URL is the standard miot-spec endpoint for any model."""
    c = _signed_connector()
    captured = {}

    def fake_encrypted_call(url, params):
        captured["url"] = url
        captured["params"] = params
        return {"result": {"code": 0}}

    with patch.object(c, "_encrypted_call", side_effect=fake_encrypted_call):
        c.call_action("us", "did-42", siid=2, aiid=10, params=["x"])
    assert captured["url"] == "https://us.api.io.mi.com/app/miotspec/action"


def test_call_action_payload_carries_did_siid_aiid_in():
    """The payload is the generic miot-spec shape — no model-specific fields."""
    c = _signed_connector()
    captured = {}

    def fake_encrypted_call(url, params):
        captured["params"] = params
        return {"result": {"code": 0}}

    with patch.object(c, "_encrypted_call", side_effect=fake_encrypted_call):
        c.call_action("us", "did-42", siid=6, aiid=7, params=["a", "b"])
    # The outer `data` wraps an inner `params` object with the action call shape.
    inner = json.loads(captured["params"]["data"])["params"]
    assert inner == {"did": "did-42", "siid": 6, "aiid": 7, "in": ["a", "b"]}


def test_call_action_defaults_params_to_empty_list_when_none():
    """A None params (actions that take no input) becomes an empty `in` list."""
    c = _signed_connector()
    captured = {}

    def fake_encrypted_call(url, params):
        captured["params"] = params
        return {"result": {"code": 0}}

    with patch.object(c, "_encrypted_call", side_effect=fake_encrypted_call):
        c.call_action("us", "did-42", siid=6, aiid=7, params=None)
    inner = json.loads(captured["params"]["data"])["params"]
    assert inner["in"] == []


def test_call_action_returns_none_when_encrypted_call_returns_none():
    """A failed encrypted call (offline / 5xx) surfaces as None, not an exception."""
    c = _signed_connector()
    with patch.object(c, "_encrypted_call", return_value=None):
        assert c.call_action("us", "d", siid=2, aiid=1, params=None) is None


def test_call_action_returns_response_body_on_success():
    """A successful call returns the decoded JSON body to the caller verbatim."""
    c = _signed_connector()
    body = {"result": {"code": 0, "message": "ok"}}
    with patch.object(c, "_encrypted_call", return_value=body):
        assert c.call_action("us", "d", siid=2, aiid=1, params=None) == body


@pytest.mark.parametrize(
    "model",
    ["xiaomi.vacuum.d109gl", "xiaomi.vacuum.b108gl"],
    ids=["x20_max_d109gl", "s20_plus_b108gl"],
)
def test_every_model_action_round_trips_through_call_action(model):
    """For each supported model, every spec action survives the generic cloud path."""
    from custom_components.xiaomi_vacuum.spec import MODELS

    spec = MODELS[model]
    actions = spec.actions
    pairs = [
        ("start_sweep", actions.start_sweep),
        ("stop_sweeping", actions.stop_sweeping),
        ("return_home", actions.return_home),
        ("start_only_sweep", actions.start_only_sweep),
        ("start_mop", actions.start_mop),
        ("start_sweep_mop", actions.start_sweep_mop),
        ("pause_sweeping", actions.pause_sweeping),
        ("continue_sweep", actions.continue_sweep),
        ("identify", actions.identify),
        ("start_room_sweep", actions.start_room_sweep),
        ("set_room_clean_configs", actions.set_room_clean_configs),
        ("start_custom_sweep", actions.start_custom_sweep),
        ("start_dust_arrest", actions.start_dust_arrest),
        ("start_mop_wash", actions.start_mop_wash),
        ("start_dry", actions.start_dry),
        ("stop_mop_wash", actions.stop_mop_wash),
        ("stop_dry", actions.stop_dry),
    ]
    c = _signed_connector()
    seen: list[tuple[int, int]] = []

    def fake_encrypted_call(url, params):
        inner = json.loads(params["data"])["params"]
        seen.append((inner["siid"], inner["aiid"]))
        assert inner["did"] == "did-test"
        assert inner["in"] == []
        assert url == "https://us.api.io.mi.com/app/miotspec/action"
        return {"result": {"code": 0}}

    with patch.object(c, "_encrypted_call", side_effect=fake_encrypted_call):
        for _name, addr in pairs:
            if addr is None:  # optional action the model doesn't have
                continue
            c.call_action("us", "did-test", addr["siid"], addr["aiid"], params=[])

    # Every non-None action of this model must have produced exactly one cloud
    # call carrying its own (siid, aiid) — proving the endpoint doesn't rewrite
    # or assume anything about the active model.
    expected = {
        (addr["siid"], addr["aiid"]) for _name, addr in pairs if addr is not None
    }
    assert set(seen) == expected
    # Each action called exactly once (no model-specific short-circuit / dedupe).
    assert len(seen) == len(expected)
