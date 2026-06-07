from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.xiaomi_vacuum.map_coordinator import (
    MAP_UPDATE_INTERVAL,
    XiaomiVacuumMapCoordinator,
)


def _state_coord(map_obj_name="0/abc"):
    sc = MagicMock()
    sc.data = {"map_obj_name": map_obj_name} if map_obj_name else {}
    sc.config_entry.entry_id = "test-entry"
    return sc


def _cloud(map_bytes=b"BIN"):
    cloud = MagicMock()
    cloud.async_get_map_bytes = AsyncMock(return_value=map_bytes)
    return cloud


def test_update_interval_is_60s():
    from datetime import timedelta

    assert timedelta(seconds=60) == MAP_UPDATE_INTERVAL


async def test_update_returns_data_when_state_data_is_none(hass):
    # Regression: robot offline since startup → state coordinator never
    # succeeded → data is None; must keep serving the cache, not crash.
    sc = _state_coord()
    sc.data = None
    coord = XiaomiVacuumMapCoordinator(hass, _cloud(), sc)
    coord.data = b"RESTORED"
    assert await coord._async_update_data() == b"RESTORED"


async def test_update_persists_png_to_store(hass, hass_storage):
    cloud = _cloud()
    coord = XiaomiVacuumMapCoordinator(hass, cloud, _state_coord())
    map_data = MagicMock()

    def fake_save(buf, format):  # noqa: A002
        buf.write(b"FAKEPNG")

    map_data.image.data.save = fake_save
    coord._parser = MagicMock()
    coord._parser.parse = MagicMock(return_value=map_data)
    assert await coord._async_update_data() == b"FAKEPNG"

    import base64

    stored = hass_storage["xiaomi_vacuum.map_test-entry"]["data"]
    assert base64.b64decode(stored["png_b64"]) == b"FAKEPNG"


async def test_async_load_cached_restores_png(hass, hass_storage):
    import base64

    hass_storage["xiaomi_vacuum.map_test-entry"] = {
        "version": 1,
        "key": "xiaomi_vacuum.map_test-entry",
        "data": {"png_b64": base64.b64encode(b"CACHEDPNG").decode()},
    }
    coord = XiaomiVacuumMapCoordinator(hass, _cloud(), _state_coord())
    await coord.async_load_cached()
    assert coord.data == b"CACHEDPNG"


async def test_async_load_cached_noop_when_store_empty(hass):
    coord = XiaomiVacuumMapCoordinator(hass, _cloud(), _state_coord())
    await coord.async_load_cached()
    assert coord.data is None


async def test_async_load_cached_ignores_corrupt_payload(hass, hass_storage):
    hass_storage["xiaomi_vacuum.map_test-entry"] = {
        "version": 1,
        "key": "xiaomi_vacuum.map_test-entry",
        "data": {"png_b64": "!!!not base64!!!"},
    }
    coord = XiaomiVacuumMapCoordinator(hass, _cloud(), _state_coord())
    await coord.async_load_cached()
    assert coord.data is None


async def test_update_returns_data_when_no_map_obj_name(hass):
    coord = XiaomiVacuumMapCoordinator(hass, _cloud(), _state_coord(map_obj_name=None))
    coord.data = b"PREVIOUS"
    result = await coord._async_update_data()
    assert result == b"PREVIOUS"


async def test_update_returns_data_when_cloud_returns_no_bytes(hass):
    coord = XiaomiVacuumMapCoordinator(hass, _cloud(map_bytes=None), _state_coord())
    coord.data = b"OLD"
    result = await coord._async_update_data()
    assert result == b"OLD"


async def test_update_skips_parse_when_blob_unchanged(hass):
    cloud = _cloud(map_bytes=b"BIN")
    coord = XiaomiVacuumMapCoordinator(hass, cloud, _state_coord())
    coord.data = b"RENDERED"
    coord._last_raw = b"BIN"
    coord._parser = MagicMock()
    result = await coord._async_update_data()
    assert result == b"RENDERED"
    coord._parser.parse.assert_not_called()


async def test_update_returns_data_when_parser_returns_no_image(hass):
    cloud = _cloud()
    coord = XiaomiVacuumMapCoordinator(hass, cloud, _state_coord())
    coord.data = b"OLD"
    coord._parser = MagicMock()
    coord._parser.parse = MagicMock(return_value=None)
    result = await coord._async_update_data()
    assert result == b"OLD"


async def test_update_returns_png_bytes_on_success(hass):
    cloud = _cloud()
    coord = XiaomiVacuumMapCoordinator(hass, cloud, _state_coord())
    map_data = MagicMock()

    def fake_save(buf, format):  # noqa: A002
        buf.write(b"FAKEPNG")

    map_data.image.data.save = fake_save
    coord._parser = MagicMock()
    coord._parser.parse = MagicMock(return_value=map_data)
    result = await coord._async_update_data()
    assert result == b"FAKEPNG"


async def test_update_raises_update_failed_on_exception(hass):
    cloud = _cloud()
    cloud.async_get_map_bytes = AsyncMock(side_effect=RuntimeError("boom"))
    coord = XiaomiVacuumMapCoordinator(hass, cloud, _state_coord())
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()


def test_extract_obj_name_from_json_envelope():
    raw = '{"index":123,"obj_name":"a/b/c"}'
    assert XiaomiVacuumMapCoordinator._extract_obj_name(raw) == "a/b/c"


def test_extract_obj_name_falls_back_to_raw_when_not_json():
    s = "plain/string"
    assert XiaomiVacuumMapCoordinator._extract_obj_name(s) == s


def test_extract_obj_name_returns_none_for_empty():
    assert XiaomiVacuumMapCoordinator._extract_obj_name(None) is None
    assert XiaomiVacuumMapCoordinator._extract_obj_name("") is None


async def test_update_skips_when_no_device_resolved(hass):
    cloud = _cloud()
    cloud._device = None
    coord = XiaomiVacuumMapCoordinator(hass, cloud, _state_coord())
    coord.data = b"OLD"
    assert await coord._async_update_data() == b"OLD"


def test_parse_blob_normalizes_model_key(hass):
    cloud = _cloud()
    coord = XiaomiVacuumMapCoordinator(hass, cloud, _state_coord())
    coord._parser = MagicMock()
    coord._parser.unpack_map = MagicMock(return_value="{}")
    coord._parser.parse = MagicMock(return_value=MagicMock())
    coord._parse_blob(b"raw", "xiaomi.vacuum.d109gl", "1234")
    # model_key should be `mi.vacuum.d109gl` (16 chars, AES key length)
    assert coord._parser.unpack_map.call_args.kwargs["model"] == "mi.vacuum.d109gl"
    assert coord._parser.unpack_map.call_args.kwargs["device_id"] == "1234"


def test_parse_blob_unwraps_base64_envelope(hass):
    import base64

    cloud = _cloud()
    coord = XiaomiVacuumMapCoordinator(hass, cloud, _state_coord())
    coord._parser = MagicMock()
    coord._parser.unpack_map = MagicMock(return_value="{}")
    coord._parser.parse = MagicMock(return_value=MagicMock())
    inner = b"INNER"
    wrapped = b'{"data":"' + base64.encodebytes(inner).strip() + b'"}'
    coord._parse_blob(wrapped, "xiaomi.vacuum.d109gl", "1")
    # After unwrapping, hex of inner bytes should be passed to unpack_map
    assert coord._parser.unpack_map.call_args.args[0] == inner.hex()
