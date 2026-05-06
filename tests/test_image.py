from __future__ import annotations


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
    coord.async_set_updated_data(b"NEWPNG")
    await hass.async_block_till_done()
    from homeassistant.components.image import async_get_image

    img = await async_get_image(hass, "image.aspirador_map")
    assert img.content == b"NEWPNG"


async def test_image_handle_new_map_updates_state(hass, setup_integration_with_cloud):
    state_before = hass.states.get("image.aspirador_map")
    coord = setup_integration_with_cloud.runtime_data.map_coordinator
    coord.async_set_updated_data(b"AGAIN")
    await hass.async_block_till_done()
    state_after = hass.states.get("image.aspirador_map")
    assert state_after.state != state_before.state
