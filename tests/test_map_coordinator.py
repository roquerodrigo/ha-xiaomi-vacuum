from __future__ import annotations

from types import SimpleNamespace
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


MAP_DATA = SimpleNamespace(
    origin_x=-2750.0, origin_y=-7800.0, resolution=50.0, width=115, height=241
)

CALIBRATION = {
    "origin_x": -2750.0,
    "origin_y": -7800.0,
    "resolution": 50.0,
    "width": 115,
    "height": 241,
    "scale": 8.0,
    "border": 12,
}


def _rendered(png=b"FAKEPNG", calibration=CALIBRATION):
    return {"png": png, "calibration": calibration}


def _fake_pipeline(coord, png=b"FAKEPNG", render_error=None, parse_error=None):
    """Replace the SDK decrypt / parse / render trio with fakes."""
    coord._decryptor = MagicMock()
    coord._decryptor.decrypt = MagicMock(return_value={"payload": True})
    coord._parser = MagicMock()
    coord._parser.parse = MagicMock(return_value=MAP_DATA, side_effect=parse_error)
    coord._renderer = MagicMock()
    coord._renderer.render = MagicMock(return_value=png, side_effect=render_error)


def test_update_interval_is_60s():
    from datetime import timedelta

    assert timedelta(seconds=60) == MAP_UPDATE_INTERVAL


async def test_update_returns_data_when_state_data_is_none(hass):
    # Regression: robot offline since startup → state coordinator never
    # succeeded → data is None; must keep serving the cache, not crash.
    sc = _state_coord()
    sc.data = None
    coord = XiaomiVacuumMapCoordinator(hass, _cloud(), sc)
    coord.data = _rendered(b"RESTORED")
    assert await coord._async_update_data() == _rendered(b"RESTORED")


async def test_update_persists_png_and_calibration_to_store(hass, hass_storage):
    cloud = _cloud()
    coord = XiaomiVacuumMapCoordinator(hass, cloud, _state_coord())
    _fake_pipeline(coord)
    assert await coord._async_update_data() == _rendered()

    import base64

    stored = hass_storage["xiaomi_vacuum.map_test-entry"]["data"]
    assert base64.b64decode(stored["png_b64"]) == b"FAKEPNG"
    assert stored["calibration"] == CALIBRATION


async def test_async_load_cached_restores_png_and_calibration(hass, hass_storage):
    import base64

    hass_storage["xiaomi_vacuum.map_test-entry"] = {
        "version": 1,
        "key": "xiaomi_vacuum.map_test-entry",
        "data": {
            "png_b64": base64.b64encode(b"CACHEDPNG").decode(),
            "calibration": CALIBRATION,
        },
    }
    coord = XiaomiVacuumMapCoordinator(hass, _cloud(), _state_coord())
    await coord.async_load_cached()
    assert coord.data == _rendered(b"CACHEDPNG")


async def test_async_load_cached_tolerates_legacy_png_only_cache(hass, hass_storage):
    """A cache written before calibration existed still restores the PNG."""
    import base64

    hass_storage["xiaomi_vacuum.map_test-entry"] = {
        "version": 1,
        "key": "xiaomi_vacuum.map_test-entry",
        "data": {"png_b64": base64.b64encode(b"CACHEDPNG").decode()},
    }
    coord = XiaomiVacuumMapCoordinator(hass, _cloud(), _state_coord())
    await coord.async_load_cached()
    assert coord.data == _rendered(b"CACHEDPNG", calibration=None)


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
    coord.data = _rendered(b"PREVIOUS")
    result = await coord._async_update_data()
    assert result == _rendered(b"PREVIOUS")


async def test_update_returns_data_when_cloud_returns_no_bytes(hass):
    coord = XiaomiVacuumMapCoordinator(hass, _cloud(map_bytes=None), _state_coord())
    coord.data = _rendered(b"OLD")
    result = await coord._async_update_data()
    assert result == _rendered(b"OLD")


async def test_update_skips_parse_when_blob_unchanged(hass):
    cloud = _cloud(map_bytes=b"BIN")
    coord = XiaomiVacuumMapCoordinator(hass, cloud, _state_coord())
    coord.data = _rendered(b"RENDERED")
    coord._last_raw = b"BIN"
    _fake_pipeline(coord)
    result = await coord._async_update_data()
    assert result == _rendered(b"RENDERED")
    coord._renderer.render.assert_not_called()


async def test_update_returns_data_when_payload_has_no_image(hass):
    from xiaomi_vacuum_sdk import MapParseError

    cloud = _cloud()
    coord = XiaomiVacuumMapCoordinator(hass, cloud, _state_coord())
    coord.data = _rendered(b"OLD")
    _fake_pipeline(coord, parse_error=MapParseError("no map image"))
    result = await coord._async_update_data()
    assert result == _rendered(b"OLD")


async def test_update_returns_rendered_map_on_success(hass):
    cloud = _cloud()
    coord = XiaomiVacuumMapCoordinator(hass, cloud, _state_coord())
    _fake_pipeline(coord)
    result = await coord._async_update_data()
    assert result == _rendered()


async def test_update_retries_parse_after_failure_with_same_blob(hass):
    """A failed parse must not mark the blob as seen — the next poll retries."""
    cloud = _cloud(map_bytes=b"BIN")
    coord = XiaomiVacuumMapCoordinator(hass, cloud, _state_coord())
    _fake_pipeline(coord, render_error=RuntimeError("bad blob"))
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()
    assert coord._renderer.render.call_count == 2
    assert coord._last_raw is None


async def test_update_raises_update_failed_on_exception(hass):
    cloud = _cloud()
    cloud.async_get_map_bytes = AsyncMock(side_effect=RuntimeError("boom"))
    coord = XiaomiVacuumMapCoordinator(hass, cloud, _state_coord())
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()


async def test_update_starts_reauth_and_keeps_map_when_session_expired(hass):
    from custom_components.xiaomi_vacuum.cloud import XiaomiCloudAuthError

    cloud = _cloud()
    cloud.async_get_map_bytes = AsyncMock(
        side_effect=XiaomiCloudAuthError("HTTP 426: SERVICETOKEN_EXPIRED")
    )
    state_coord = _state_coord()
    coord = XiaomiVacuumMapCoordinator(hass, cloud, state_coord)
    coord.data = _rendered(b"CACHED")
    result = await coord._async_update_data()
    assert result == _rendered(b"CACHED")
    state_coord.config_entry.async_start_reauth.assert_called_once_with(hass)


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
    cloud.device = None
    coord = XiaomiVacuumMapCoordinator(hass, cloud, _state_coord())
    coord.data = _rendered(b"OLD")
    assert await coord._async_update_data() == _rendered(b"OLD")


def test_render_blob_passes_model_and_device_id(hass):
    cloud = _cloud()
    coord = XiaomiVacuumMapCoordinator(hass, cloud, _state_coord())
    _fake_pipeline(coord, png=b"P")
    rendered = coord._render_blob(b"raw", "xiaomi.vacuum.d109gl", "1234")
    # The SDK owns the `xiaomi.` -> `mi.` key normalization; the coordinator
    # hands over the full model string and the blob untouched.
    coord._renderer.render.assert_called_once_with(
        b"raw", model="xiaomi.vacuum.d109gl", device_id="1234"
    )
    coord._decryptor.decrypt.assert_called_once_with(
        b"raw", "xiaomi.vacuum.d109gl", "1234"
    )
    assert rendered == _rendered(b"P")


def test_render_blob_calibration_mirrors_render_options(hass):
    """The calibration reports the scale / border the renderer actually used."""
    from xiaomi_vacuum_sdk import RenderOptions

    coord = XiaomiVacuumMapCoordinator(hass, _cloud(), _state_coord())
    _fake_pipeline(coord)
    rendered = coord._render_blob(b"raw", "xiaomi.vacuum.d109gl", "1")
    assert rendered["calibration"]["scale"] == RenderOptions().scale
    assert rendered["calibration"]["border"] == RenderOptions().border


def test_render_blob_returns_none_when_payload_not_drawable(hass):
    from xiaomi_vacuum_sdk import MapParseError

    cloud = _cloud()
    coord = XiaomiVacuumMapCoordinator(hass, cloud, _state_coord())
    _fake_pipeline(coord, parse_error=MapParseError("no map image"))
    assert coord._render_blob(b"raw", "xiaomi.vacuum.d109gl", "1") is None


def test_render_blob_returns_none_when_render_rejects_payload(hass):
    """A parse error raised by the renderer itself is handled the same way."""
    from xiaomi_vacuum_sdk import MapParseError

    coord = XiaomiVacuumMapCoordinator(hass, _cloud(), _state_coord())
    _fake_pipeline(coord, render_error=MapParseError("no map image"))
    assert coord._render_blob(b"raw", "xiaomi.vacuum.d109gl", "1") is None


def test_render_blob_propagates_decrypt_errors(hass):
    """A blob that does not decrypt is a real failure, retried by the next poll."""
    from xiaomi_vacuum_sdk import MapDecryptError

    coord = XiaomiVacuumMapCoordinator(hass, _cloud(), _state_coord())
    _fake_pipeline(coord)
    coord._decryptor.decrypt = MagicMock(side_effect=MapDecryptError("bad key"))
    with pytest.raises(MapDecryptError):
        coord._render_blob(b"raw", "xiaomi.vacuum.d109gl", "1")
