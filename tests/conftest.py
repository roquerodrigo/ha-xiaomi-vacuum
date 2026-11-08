from __future__ import annotations

import json
from contextlib import ExitStack, contextmanager
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from xiaomi_vacuum_sdk import CoordinateSystem, RenderOptions

if TYPE_CHECKING:
    from collections.abc import Generator


pytest_plugins = "pytest_homeassistant_custom_component"

# What MapRenderer.render_map hands back: the PNG plus the geometry it drew
# with, so the coordinator derives its calibration from a realistic shape.
RENDERED_MAP = SimpleNamespace(
    png=b"png-bytes",
    map_data=SimpleNamespace(width=115, height=241, segments=()),
    coordinates=CoordinateSystem(
        origin_x=-2750.0,
        origin_y=-7800.0,
        resolution=50.0,
        grid_height=241,
        scale=RenderOptions().scale,
        offset=RenderOptions().border,
    ),
)

SAMPLE_ROOM_INFO = json.dumps(
    {
        "rooms": [
            {"id": 10, "name": "Office"},
            {"id": 28, "name": "Living room"},
        ],
        "map_uid": 5,
    }
)

SAMPLE_STATE: dict[str, Any] = {
    "status": 2,
    "fault_ids": '{"ts": 1700000000, "fault": [0]}',
    "sweep_mop_type": 1,
    "cleaning_area": 200,
    "cleaning_time": 120,
    "clean_times": 1,
    "fan_speed": 2,
    "mop_water_level": 1,
    "mop_status": True,
    "room_information": SAMPLE_ROOM_INFO,
    "last_clean_time": 1700000000,
    "sweep_route": 2,
    "obstacle_avoidance_strategy": 0,
    "battery_level": 99,
    "charging_state": 1,
    "mop_life": 85,
    "main_brush_life": 71,
    "side_brush_life": 90,
    "filter_life": 70,
    # No map yet: the cloud fixtures publish one when a test needs it.
    "map_obj_name": None,
}

#: Parsed-state fixture for the X20 Max (alias of SAMPLE_STATE for clarity).
_SAMPLE_STATE_D109: dict[str, Any] = SAMPLE_STATE

#: Parsed-state fixture for the S40 Pro. Same property layout as the X20 Max;
#: status 22 is one of the station-assisted washing codes only this model has.
_SAMPLE_STATE_OV71: dict[str, Any] = {**SAMPLE_STATE, "status": 22}

#: Parsed-state fixture for the S20+. Uses the plain `fault` property, exposes no
#: last_clean_time / sweep_route / obstacle_avoidance (the S20+ has none), and the
#: room-information key maps to the S20+ SIID-6/PIID-10 property.
_SAMPLE_STATE_B108: dict[str, Any] = {
    "status": 2,
    "fault": 0,
    "sweep_mop_type": 1,
    "cleaning_area": 200,
    "cleaning_time": 120,
    "clean_times": 1,
    "fan_speed": 2,
    "mop_water_level": 1,
    "mop_status": True,
    "room_information": SAMPLE_ROOM_INFO,
    "battery_level": 99,
    "charging_state": 1,
    "mop_life": 85,
    "main_brush_life": 71,
    "side_brush_life": 90,
    "filter_life": 70,
    "map_obj_name": None,
}

#: Parsed-state fixture for the X20+, taken from a live unit docked and fully
#: charged: Dreame fault 68 (mop pads on, docked) is a notice, task status 0 is
#: "no job open". No sweep/mop type, clean times, room information or map name.
_SAMPLE_STATE_C102: dict[str, Any] = {
    "status": 13,
    "task_status": 0,
    "fault": 68,
    "cleaning_area": 19,
    "cleaning_time": 25,
    "fan_speed": 1,
    "mop_water_level": 2,
    "mop_status": 1,
    "battery_level": 100,
    "charging_state": 1,
    "mop_life": 0,
    "main_brush_life": 0,
    "side_brush_life": 0,
    "filter_life": 0,
    "map_obj_name": '{"object_name":"1234/567/map.bin","md5":"abc"}',
    # Raw clean-setting: mode bits 3 (sweep before mopping) under other settings.
    "sweep_mop_type": 133123,
    "main_brush_time_left": 120,
    "side_brush_time_left": 80,
    "filter_time_left": 300,
    "mop_time_left": 40,
    "drying_time_left": 0,
    "total_clean_time": 23000,
    "total_clean_count": 878,
    "total_clean_area": 16233,
    "resume_after_charge": 1,
    "carpet_boost": 1,
    "child_lock": 0,
    "do_not_disturb": True,
    "volume": 75,
}

#: One entry per supported model: the parsed state its mocked device publishes
#: and the identity of its config entry. Adding a model adds one entry here; the
#: contract tests run against every entry and fail when a model has none.
MODEL_FIXTURES: dict[str, dict[str, Any]] = {
    "xiaomi.vacuum.d109gl": {
        "mac": "AA:BB:CC:DD:EE:FF",
        "host": "192.168.1.50",
        "name": "Vacuum",
        "state": _SAMPLE_STATE_D109,
    },
    "xiaomi.vacuum.b108gl": {
        "mac": "AA:BB:CC:DD:EE:01",
        "host": "192.168.1.51",
        "name": "S20 Living Room",
        "state": _SAMPLE_STATE_B108,
    },
    "xiaomi.vacuum.ov71gl": {
        "mac": "AA:BB:CC:DD:EE:02",
        "host": "192.168.1.52",
        "name": "S40 Pro",
        "state": _SAMPLE_STATE_OV71,
    },
    "xiaomi.vacuum.c102gl": {
        "mac": "AA:BB:CC:DD:EE:03",
        "host": "192.168.1.53",
        "name": "X20 Plus",
        "state": _SAMPLE_STATE_C102,
    },
}


@pytest.fixture
def sample_state() -> dict[str, Any]:
    return dict(SAMPLE_STATE)


@pytest.fixture
def sample_room_info() -> str:
    return SAMPLE_ROOM_INFO


@pytest.fixture
def enable_custom_integrations(hass) -> None:
    from homeassistant.loader import DATA_CUSTOM_COMPONENTS

    hass.data.pop(DATA_CUSTOM_COMPONENTS, None)


def _make_miot_instance(model: str):
    """Build a mocked xiaomi-vacuum-sdk MiotClient instance for a model string."""
    from custom_components.xiaomi_vacuum.spec import get_spec

    spec = get_spec(model)
    # Distinct MAC per model so entries don't collide on unique_id.
    mac = MODEL_FIXTURES[model]["mac"]
    instance = MagicMock()
    info = MagicMock()
    info.model = model
    info.mac_address = mac
    info.firmware_version = "1.0.0"
    info.hardware_version = "rev1"
    info.raw = {"model": model, "mac": mac}
    instance.info = AsyncMock(return_value=info)
    instance.set_property = AsyncMock(return_value=None)
    instance.call_action = AsyncMock(return_value=None)
    instance.close = AsyncMock(return_value=None)
    state = MODEL_FIXTURES[model]["state"]
    instance.get_properties = AsyncMock(
        side_effect=lambda mapping, **_: {name: state.get(name) for name in mapping}
    )
    instance._spec = spec  # exposed for tests that assert on the spec
    return instance


@pytest.fixture
def make_miot_instance():
    """Factory for a mocked MiotClient instance of any supported model."""
    return _make_miot_instance


def _patch_miot_client(model: str) -> Generator:
    """Patch the SDK MiotClient everywhere it's imported with a model's mock."""
    with patch("custom_components.xiaomi_vacuum.api.client.MiotClient") as cls:
        cls.return_value = _make_miot_instance(model)
        yield cls.return_value


async def _setup_model_entry(hass, model: str):
    """Add and set up a config entry for ``model``'s mocked device."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.xiaomi_vacuum.const import (
        CONF_HOST,
        CONF_NAME,
        CONF_TOKEN,
        DOMAIN,
    )

    fixture = MODEL_FIXTURES[model]
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: fixture["host"],
            CONF_TOKEN: "0" * 32,
            CONF_NAME: fixture["name"],
        },
        unique_id=fixture["mac"],
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.fixture
async def setup_model(hass, enable_custom_integrations):
    """
    Set up any model by its model string: ``entry, device = await setup_model(m)``.

    ``device`` is the mocked MiotClient instance, patched until the test ends.
    """
    with ExitStack() as stack:

        async def setup(model: str):
            device = stack.enter_context(contextmanager(_patch_miot_client)(model))
            return await _setup_model_entry(hass, model), device

        yield setup


@pytest.fixture(params=sorted(MODEL_FIXTURES))
def model(request) -> str:
    """Every supported model string, one test run each."""
    return request.param


@pytest.fixture
def mock_miot_device_of_model(model) -> Generator:
    """Patch the SDK MiotClient with the parametrized model's mock."""
    yield from _patch_miot_client(model)


@pytest.fixture
async def setup_integration_of_model(
    hass, model, mock_miot_device_of_model, enable_custom_integrations
):
    """Set up the integration against the parametrized model's mock."""
    return await _setup_model_entry(hass, model)


@pytest.fixture
def mock_miot_device() -> Generator:
    """Patch the SDK MiotClient for the X20 Max (d109gl), the default model."""
    yield from _patch_miot_client("xiaomi.vacuum.d109gl")


@pytest.fixture
def mock_miot_device_b108() -> Generator:
    """Patch the SDK MiotClient for the S20+ (b108gl) model."""
    yield from _patch_miot_client("xiaomi.vacuum.b108gl")


@pytest.fixture
def mock_miot_device_ov71() -> Generator:
    """Patch the SDK MiotClient for the S40 Pro (ov71gl) model."""
    yield from _patch_miot_client("xiaomi.vacuum.ov71gl")


@pytest.fixture
def mock_miot_device_c102() -> Generator:
    """Patch the SDK MiotClient for the X20+ (c102gl) model."""
    yield from _patch_miot_client("xiaomi.vacuum.c102gl")


@pytest.fixture
async def setup_integration(hass, mock_miot_device, enable_custom_integrations):
    """Set up the integration against the X20 Max mock and return the entry."""
    return await _setup_model_entry(hass, "xiaomi.vacuum.d109gl")


@pytest.fixture
async def setup_integration_b108(
    hass, mock_miot_device_b108, enable_custom_integrations
):
    """Set up the integration against the S20+ (b108gl) mock and return the entry."""
    return await _setup_model_entry(hass, "xiaomi.vacuum.b108gl")


@pytest.fixture
async def setup_integration_ov71(
    hass, mock_miot_device_ov71, enable_custom_integrations
):
    """Set up the integration against the S40 Pro (ov71gl) mock and return the entry."""
    return await _setup_model_entry(hass, "xiaomi.vacuum.ov71gl")


@pytest.fixture
async def setup_integration_c102(
    hass, mock_miot_device_c102, enable_custom_integrations
):
    """Set up the integration against the X20+ (c102gl) mock and return the entry."""
    return await _setup_model_entry(hass, "xiaomi.vacuum.c102gl")


def build_dreame_map(
    rooms: dict[str, dict[str, Any]] | None,
    *,
    envelope: bool = True,
    key: str = "",
) -> bytes:
    """Build a Dreame cloud map blob with ``rooms`` as its ``seg_inf``."""
    import base64
    import json
    import zlib

    width, height = 4, 3
    header = bytearray(27)
    header[17:19] = (50).to_bytes(2, "little")  # millimetres per cell
    header[19:21] = width.to_bytes(2, "little")
    header[21:23] = height.to_bytes(2, "little")
    trailer = b"" if rooms is None else json.dumps({"seg_inf": rooms}).encode()
    frame = bytes(header) + bytes(width * height) + trailer
    encoded = base64.b64encode(zlib.compress(frame)).decode()
    encoded = encoded.replace("/", "_").replace("+", "-").rstrip("=")
    if key:
        encoded = f"{encoded},{key}"
    if not envelope:
        return encoded.encode()
    maps = [
        {"id": 0, "name": "", "angle": "0", "map": "not-the-current-map"},
        {"id": 7, "name": "", "angle": "0", "map": encoded},
    ]
    return json.dumps({"mapstr": maps, "curr_id": 7}).encode()


def b64_name(name: str) -> str:
    """Encode a room name the way Dreame stores it in ``seg_inf``."""
    import base64

    return base64.b64encode(name.encode()).decode()


@pytest.fixture
def dreame_map():
    """Factory building Dreame cloud map blobs (see :func:`build_dreame_map`)."""
    return build_dreame_map


@pytest.fixture
def dreame_name():
    """Encoder for Dreame base64 room names."""
    return b64_name


@pytest.fixture
def mock_cloud() -> Generator:
    """Mock XiaomiCloud (covers both `from_session` and `__init__` paths)."""
    with patch("custom_components.xiaomi_vacuum.XiaomiCloud") as cls:
        instance = cls.return_value
        cls.from_session = MagicMock(return_value=instance)
        device = MagicMock(country="cn", model="xiaomi.vacuum.d109gl", device_id="d")
        instance._device = device
        instance.async_resolve_device = AsyncMock(return_value=device)
        instance.async_get_map_bytes = AsyncMock(return_value=b"PNG_BYTES")
        yield instance


@pytest.fixture
async def setup_integration_c102_with_cloud(
    hass, mock_miot_device_c102, mock_cloud, enable_custom_integrations
):
    """Set up the X20+ with a cloud session; its Dreame map is never rendered."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    # The sample state carries the docked-with-mop notice (fault 68).
    mock_cloud.async_fault_text = AsyncMock(return_value=None)
    mock_cloud.async_get_map_bytes = AsyncMock(
        return_value=build_dreame_map({"1": {"name": b64_name("Living room")}})
    )

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
            CONF_HOST: "192.168.1.53",
            CONF_TOKEN: "0" * 32,
            CONF_NAME: "X20 Plus",
            CONF_CLOUD_COUNTRY: "de",
            CONF_CLOUD_SSECURITY: "ssecurity_value",
            CONF_CLOUD_SERVICE_TOKEN: "service_token_value",
            CONF_CLOUD_USER_ID: "user_id_value",
        },
        unique_id="AA:BB:CC:DD:EE:03",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.fixture
async def setup_integration_with_cloud(
    hass, mock_miot_device, mock_cloud, enable_custom_integrations
):
    """Set up the integration with cloud session tokens populated."""
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

    with patch(
        "custom_components.xiaomi_vacuum.map_coordinator.MapRenderer"
    ) as renderer_cls:
        renderer_cls.return_value.render_map = MagicMock(return_value=RENDERED_MAP)

        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "192.168.1.50",
                CONF_TOKEN: "0" * 32,
                CONF_NAME: "Vacuum",
                CONF_CLOUD_COUNTRY: "cn",
                CONF_CLOUD_SSECURITY: "ssecurity_value",
                CONF_CLOUD_SERVICE_TOKEN: "service_token_value",
                CONF_CLOUD_USER_ID: "user_id_value",
            },
            unique_id="AA:BB:CC:DD:EE:FF",
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        yield entry
