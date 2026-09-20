from __future__ import annotations

CALIBRATION = {
    "origin_x": -2750.0,
    "origin_y": -7800.0,
    "resolution": 50.0,
    "width": 115,
    "height": 241,
    "scale": 8.0,
    "border": 12,
}


def _rendered(png, calibration=CALIBRATION):
    return {"png": png, "calibration": calibration}


async def test_no_image_entity_without_cloud(hass, setup_integration):
    states = hass.states.async_all("image")
    assert len(states) == 0


async def test_image_entity_created_when_cloud_configured(
    hass, setup_integration_with_cloud
):
    states = hass.states.async_all("image")
    assert len(states) == 1


async def test_image_entity_serves_map_coordinator_data(
    hass, setup_integration_with_cloud
):
    coord = setup_integration_with_cloud.runtime_data.map_coordinator
    coord.async_set_updated_data(_rendered(b"NEWPNG"))
    await hass.async_block_till_done()
    from homeassistant.components.image import async_get_image

    img = await async_get_image(hass, "image.vacuum_map")
    assert img.content == b"NEWPNG"


async def test_image_handle_new_map_updates_state(hass, setup_integration_with_cloud):
    state_before = hass.states.get("image.vacuum_map")
    coord = setup_integration_with_cloud.runtime_data.map_coordinator
    coord.async_set_updated_data(_rendered(b"AGAIN"))
    await hass.async_block_till_done()
    state_after = hass.states.get("image.vacuum_map")
    assert state_after.state != state_before.state


async def test_image_handle_new_map_ignores_identical_blob(
    hass, setup_integration_with_cloud
):
    coord = setup_integration_with_cloud.runtime_data.map_coordinator
    coord.async_set_updated_data(_rendered(b"DUPLICATE"))
    await hass.async_block_till_done()
    state_first = hass.states.get("image.vacuum_map")

    # Pushing the same bytes again must be a no-op (no new last_updated).
    coord.async_set_updated_data(_rendered(b"DUPLICATE"))
    await hass.async_block_till_done()
    state_second = hass.states.get("image.vacuum_map")
    assert state_second.last_updated == state_first.last_updated


async def test_image_unavailable_before_any_map(hass, setup_integration_with_cloud):
    # SAMPLE_STATE has no map_obj_name, so no map was ever rendered.
    state = hass.states.get("image.vacuum_map")
    assert state.state == "unavailable"


async def test_image_stays_available_when_robot_goes_offline(
    hass, setup_integration_with_cloud
):
    rt = setup_integration_with_cloud.runtime_data
    rt.map_coordinator.async_set_updated_data(_rendered(b"LASTMAP"))
    await hass.async_block_till_done()

    # Robot powered off: the state coordinator starts failing, but the map
    # entity must keep a valid state so the frontend gets an access token.
    rt.coordinator.async_set_update_error(TimeoutError("robot off"))
    await hass.async_block_till_done()

    assert hass.states.get("vacuum.vacuum").state == "unavailable"
    assert hass.states.get("image.vacuum_map").state != "unavailable"


async def test_image_restored_from_disk_cache_on_startup(
    hass, mock_miot_device, mock_cloud, enable_custom_integrations, hass_storage
):
    import base64

    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.xiaomi_vacuum.const import (
        CONF_CLOUD_COUNTRY,
        CONF_CLOUD_SERVICE_TOKEN,
        CONF_CLOUD_SSECURITY,
        CONF_CLOUD_USER_ID,
        CONF_HOST,
        CONF_NAME,
        CONF_TOKEN,
        DOMAIN,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.1.50",
            CONF_TOKEN: "0" * 32,
            CONF_NAME: "Vacuum",
            CONF_CLOUD_COUNTRY: "cn",
            CONF_CLOUD_SSECURITY: "ssec",
            CONF_CLOUD_SERVICE_TOKEN: "tok",
            CONF_CLOUD_USER_ID: "uid",
        },
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)
    hass_storage[f"{DOMAIN}.map_{entry.entry_id}"] = {
        "version": 1,
        "key": f"{DOMAIN}.map_{entry.entry_id}",
        "data": {"png_b64": base64.b64encode(b"DISKPNG").decode()},
    }
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    from homeassistant.components.image import async_get_image

    state = hass.states.get("image.vacuum_map")
    assert state.state != "unavailable"
    assert (await async_get_image(hass, "image.vacuum_map")).content == b"DISKPNG"


async def test_async_image_keeps_last_when_coordinator_clears(
    hass, setup_integration_with_cloud
):
    from homeassistant.components.image import async_get_image

    coord = setup_integration_with_cloud.runtime_data.map_coordinator
    coord.async_set_updated_data(_rendered(b"KEPT"))
    await hass.async_block_till_done()
    assert (await async_get_image(hass, "image.vacuum_map")).content == b"KEPT"

    coord.async_set_updated_data(None)
    await hass.async_block_till_done()
    assert (await async_get_image(hass, "image.vacuum_map")).content == b"KEPT"
    assert hass.states.get("image.vacuum_map").state != "unavailable"


async def test_image_exposes_calibration_points_for_the_map_card(
    hass, setup_integration_with_cloud
):
    coord = setup_integration_with_cloud.runtime_data.map_coordinator
    coord.async_set_updated_data(_rendered(b"CALIB"))
    await hass.async_block_till_done()
    state = hass.states.get("image.vacuum_map")
    assert state.attributes["calibration"] == CALIBRATION
    points = state.attributes["calibration_points"]
    # Top-left of the floor image: grid column 0, top row (grid row height-1).
    assert points[0] == {
        "map": {"x": 12, "y": 12},
        "vacuum": {"x": -2750, "y": -7800 + 240 * 50},
    }
    # Top-right: grid column `width`.
    assert points[1] == {
        "map": {"x": 12 + 115 * 8, "y": 12},
        "vacuum": {"x": -2750 + 115 * 50, "y": -7800 + 240 * 50},
    }
    # Bottom-left: one cell below grid row 0, i.e. the floor image's bottom edge.
    assert points[2] == {
        "map": {"x": 12, "y": 12 + 241 * 8},
        "vacuum": {"x": -2750, "y": -7800 - 50},
    }


async def test_image_calibration_points_round_trip_the_sdk_projection(
    hass, setup_integration_with_cloud
):
    """Every exposed pair must satisfy the SDK's own device→pixel transform."""
    from xiaomi_vacuum_sdk import MapPoint
    from xiaomi_vacuum_sdk.map.coordinate_system import CoordinateSystem

    coord = setup_integration_with_cloud.runtime_data.map_coordinator
    coord.async_set_updated_data(_rendered(b"CALIB"))
    await hass.async_block_till_done()
    system = CoordinateSystem(
        origin_x=CALIBRATION["origin_x"],
        origin_y=CALIBRATION["origin_y"],
        resolution=CALIBRATION["resolution"],
        grid_height=CALIBRATION["height"],
        scale=CALIBRATION["scale"],
        offset=CALIBRATION["border"],
    )
    for point in hass.states.get("image.vacuum_map").attributes["calibration_points"]:
        x, y = system.to_image(MapPoint(point["vacuum"]["x"], point["vacuum"]["y"]))
        assert (round(x), round(y)) == (point["map"]["x"], point["map"]["y"])


async def test_image_without_calibration_exposes_none(
    hass, setup_integration_with_cloud
):
    """A PNG restored from a legacy cache has no calibration to expose."""
    coord = setup_integration_with_cloud.runtime_data.map_coordinator
    coord.async_set_updated_data(_rendered(b"LEGACY", calibration=None))
    await hass.async_block_till_done()
    state = hass.states.get("image.vacuum_map")
    assert state.attributes["calibration"] is None
    assert state.attributes["calibration_points"] is None
