from __future__ import annotations

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
        "custom_components.xiaomi_vacuum.cloud.async_get_clientsession",
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
        "custom_components.xiaomi_vacuum.cloud.async_get_clientsession",
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
