from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.xiaomi_vacuum.cloud import XiaomiDeviceInfo
from custom_components.xiaomi_vacuum.config_flow import XiaomiVacuumFlowHandler
from custom_components.xiaomi_vacuum.const import (
    CONF_CLOUD_SERVICE_TOKEN,
    CONF_CLOUD_SSECURITY,
    CONF_CLOUD_USER_ID,
    CONF_HOST,
    CONF_NAME,
    CONF_TOKEN,
    DOMAIN,
)


async def _start(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


def _device(device_id="d1", local_ip="192.168.1.5", mac="AA:BB:CC:DD:EE:FF"):
    return XiaomiDeviceInfo(
        device_id=device_id,
        name="Vacuum",
        model="xiaomi.vacuum.d109gl",
        token="abc",
        country="us",
        local_ip=local_ip,
        mac=mac,
    )


def _handler(hass):
    handler = XiaomiVacuumFlowHandler()
    handler.hass = hass
    return handler


async def test_step_user_jumps_straight_to_qr_progress(
    hass, enable_custom_integrations
):
    """Add Hub → no form → QR progress dialog with the PNG embedded."""
    cloud = MagicMock()
    cloud.async_qr_start = AsyncMock(return_value=(b"PNG", "https://lp", 60))

    pending = asyncio.Future()

    async def hang(*_a, **_kw):
        return await pending

    cloud.async_qr_login = hang

    with patch(
        "custom_components.xiaomi_vacuum.config_flow.XiaomiCloud", return_value=cloud
    ):
        try:
            result = await _start(hass)
            assert result["type"] == FlowResultType.SHOW_PROGRESS
            assert result["step_id"] == "qr"
            assert result["progress_action"] == "waiting_for_scan"
            assert (
                "data:image/png;base64,"
                in result["description_placeholders"]["qr_image"]
            )
        finally:
            pending.cancel()
            await asyncio.sleep(0)


async def test_qr_failed_shows_retry_form(hass):
    handler = _handler(hass)
    result = await handler.async_step_qr_failed()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "qr_failed"
    assert result["errors"] == {"base": "qr_not_scanned"}


async def test_qr_failed_with_input_retries_qr(hass):
    handler = _handler(hass)
    with patch.object(
        handler, "async_step_qr", AsyncMock(return_value={"type": "retry"})
    ) as step_qr:
        result = await handler.async_step_qr_failed(user_input={})
    step_qr.assert_awaited_once()
    assert result == {"type": "retry"}


async def test_refresh_qr_handles_start_failure(hass):
    from custom_components.xiaomi_vacuum.cloud import XiaomiCloudError

    handler = _handler(hass)
    cloud = MagicMock()
    cloud.async_qr_start = AsyncMock(side_effect=XiaomiCloudError("nope"))
    handler._cloud = cloud
    await handler._refresh_qr()
    assert handler._qr_lp_url is None
    assert handler._qr_image is None


async def test_refresh_qr_populates_state_on_success(hass):
    handler = _handler(hass)
    cloud = MagicMock()
    cloud.async_qr_start = AsyncMock(return_value=(b"PNG", "https://lp", 90))
    handler._cloud = cloud
    await handler._refresh_qr()
    assert handler._qr_image == b"PNG"
    assert handler._qr_lp_url == "https://lp"
    assert handler._qr_timeout == 90


def test_qr_data_uri_empty_when_no_image(hass):
    handler = _handler(hass)
    handler._qr_image = None
    assert handler._qr_data_uri() == ""


def test_qr_data_uri_encodes_png(hass):
    handler = _handler(hass)
    handler._qr_image = b"PNG"
    assert handler._qr_data_uri().startswith("data:image/png;base64,")


async def test_qr_step_done_failed_when_refresh_yields_no_cloud(hass):
    handler = _handler(hass)
    with patch.object(handler, "_refresh_qr", AsyncMock(return_value=None)):
        handler._cloud = None
        result = await handler.async_step_qr()
    assert result["type"] == FlowResultType.SHOW_PROGRESS_DONE
    assert result["step_id"] == "qr_failed"


async def test_qr_step_progress_done_on_auth_error(hass):
    from custom_components.xiaomi_vacuum.cloud import XiaomiCloudAuthError

    handler = _handler(hass)
    task = MagicMock()
    task.done.return_value = True
    task.result.side_effect = XiaomiCloudAuthError("denied")
    handler._qr_task = task
    result = await handler.async_step_qr()
    assert result["step_id"] == "qr_failed"
    assert handler._qr_task is None


async def test_qr_step_progress_done_on_generic_cloud_error(hass):
    from custom_components.xiaomi_vacuum.cloud import XiaomiCloudError

    handler = _handler(hass)
    task = MagicMock()
    task.done.return_value = True
    task.result.side_effect = XiaomiCloudError("boom")
    handler._qr_task = task
    result = await handler.async_step_qr()
    assert result["step_id"] == "qr_failed"
    assert handler._qr_task is None


async def test_qr_step_proceeds_to_discover_on_success(hass):
    handler = _handler(hass)
    task = MagicMock()
    task.done.return_value = True
    task.result.return_value = None
    handler._qr_task = task
    result = await handler.async_step_qr()
    assert result["step_id"] == "discover"


async def test_discover_aborts_when_cloud_missing(hass):
    handler = _handler(hass)
    handler._cloud = None
    handler._devices = []
    result = await handler.async_step_discover()
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "cloud_list_failed"


async def test_discover_aborts_on_list_failure(hass):
    from custom_components.xiaomi_vacuum.cloud import XiaomiCloudError

    handler = _handler(hass)
    cloud = MagicMock()
    cloud.async_list_devices = AsyncMock(side_effect=XiaomiCloudError("api down"))
    handler._cloud = cloud
    result = await handler.async_step_discover()
    assert result["reason"] == "cloud_list_failed"


async def test_discover_aborts_when_no_vacuum_found(hass):
    handler = _handler(hass)
    cloud = MagicMock()
    cloud.async_list_devices = AsyncMock(return_value=[])
    handler._cloud = cloud
    result = await handler.async_step_discover()
    assert result["reason"] == "no_vacuum_found"


async def test_discover_auto_finalizes_single_device(hass):
    handler = _handler(hass)
    cloud = MagicMock()
    device = _device()
    cloud.async_list_devices = AsyncMock(return_value=[device])
    handler._cloud = cloud
    with patch.object(
        handler, "_finalize", AsyncMock(return_value={"type": "done"})
    ) as finalize:
        result = await handler.async_step_discover()
    finalize.assert_awaited_once_with(device)
    assert result == {"type": "done"}


async def test_discover_shows_picker_for_multiple_devices(hass):
    handler = _handler(hass)
    handler._devices = [_device(device_id="d1"), _device(device_id="d2")]
    result = await handler.async_step_discover()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "discover"


async def test_discover_finalizes_chosen_device(hass):
    handler = _handler(hass)
    d1 = _device(device_id="d1")
    d2 = _device(device_id="d2")
    handler._devices = [d1, d2]
    with patch.object(
        handler, "_finalize", AsyncMock(return_value={"type": "done"})
    ) as finalize:
        result = await handler.async_step_discover(user_input={"device": "d2"})
    finalize.assert_awaited_once_with(d2)
    assert result == {"type": "done"}


async def test_discover_reshows_picker_on_unknown_choice(hass):
    handler = _handler(hass)
    handler._devices = [_device(device_id="d1"), _device(device_id="d2")]
    result = await handler.async_step_discover(user_input={"device": "unknown"})
    assert result["type"] == FlowResultType.FORM


async def test_finalize_aborts_when_no_local_ip(hass):
    handler = _handler(hass)
    handler.async_set_unique_id = AsyncMock(return_value=None)
    handler._abort_if_unique_id_configured = MagicMock(return_value=None)
    result = await handler._finalize(_device(local_ip=None))
    assert result["reason"] == "no_local_ip"


async def test_finalize_aborts_when_local_unreachable(hass):
    from custom_components.xiaomi_vacuum.api import (
        XiaomiVacuumApiClientCommunicationError,
    )

    handler = _handler(hass)
    handler.async_set_unique_id = AsyncMock(return_value=None)
    handler._abort_if_unique_id_configured = MagicMock(return_value=None)
    client = MagicMock()
    client.async_get_info = AsyncMock(
        side_effect=XiaomiVacuumApiClientCommunicationError("timeout")
    )
    with patch(
        "custom_components.xiaomi_vacuum.config_flow.XiaomiVacuumApiClient",
        return_value=client,
    ):
        result = await handler._finalize(_device())
    assert result["reason"] == "local_unreachable"


async def test_finalize_aborts_on_local_probe_failure(hass):
    from custom_components.xiaomi_vacuum.api import XiaomiVacuumApiClientError

    handler = _handler(hass)
    handler.async_set_unique_id = AsyncMock(return_value=None)
    handler._abort_if_unique_id_configured = MagicMock(return_value=None)
    client = MagicMock()
    client.async_get_info = AsyncMock(side_effect=XiaomiVacuumApiClientError("bad"))
    with patch(
        "custom_components.xiaomi_vacuum.config_flow.XiaomiVacuumApiClient",
        return_value=client,
    ):
        result = await handler._finalize(_device())
    assert result["reason"] == "local_probe_failed"


async def test_finalize_creates_entry_on_success(hass):
    handler = _handler(hass)
    handler.async_set_unique_id = AsyncMock(return_value=None)
    handler._abort_if_unique_id_configured = MagicMock(return_value=None)
    handler._cloud = None
    handler._user_input = {}

    info = MagicMock()
    info.mac_address = "AA:BB:CC:DD:EE:FF"
    client = MagicMock()
    client.async_get_info = AsyncMock(return_value=info)
    created = {"type": FlowResultType.CREATE_ENTRY}
    with (
        patch(
            "custom_components.xiaomi_vacuum.config_flow.XiaomiVacuumApiClient",
            return_value=client,
        ),
        patch.object(handler, "async_create_entry", return_value=created),
        patch.object(
            type(handler), "unique_id", new_callable=lambda: "AA:BB:CC:DD:EE:FF"
        ),
    ):
        result = await handler._finalize(_device())
    assert result is created
    assert handler._user_input[CONF_HOST] == "192.168.1.5"
    assert handler._user_input[CONF_TOKEN] == "abc"
    assert handler._user_input[CONF_NAME] == "Vacuum"


async def test_finalize_updates_unique_id_when_mac_differs(hass):
    handler = _handler(hass)
    set_uid = AsyncMock(return_value=None)
    handler.async_set_unique_id = set_uid
    handler._abort_if_unique_id_configured = MagicMock(return_value=None)
    handler._cloud = None
    handler._user_input = {}

    info = MagicMock()
    info.mac_address = "11:22:33:44:55:66"
    client = MagicMock()
    client.async_get_info = AsyncMock(return_value=info)
    with (
        patch(
            "custom_components.xiaomi_vacuum.config_flow.XiaomiVacuumApiClient",
            return_value=client,
        ),
        patch.object(handler, "async_create_entry", return_value={"ok": True}),
        patch.object(
            type(handler), "unique_id", new_callable=lambda: "AA:BB:CC:DD:EE:FF"
        ),
    ):
        await handler._finalize(_device())
    # called once at top, then again because probed mac differs from unique_id
    assert set_uid.await_count == 2


def test_create_entry_persists_cloud_tokens(hass):
    handler = _handler(hass)
    handler._user_input = {CONF_NAME: "Vacuum"}
    cloud = MagicMock()
    cloud.session_tokens = MagicMock(
        return_value={
            "ssecurity": "S",
            "service_token": "T",
            "user_id": "U",
        }
    )
    handler._cloud = cloud
    created = {"type": FlowResultType.CREATE_ENTRY}
    with patch.object(handler, "async_create_entry", return_value=created) as create:
        result = handler._create_entry()
    assert result is created
    _, kwargs = create.call_args
    assert kwargs["data"][CONF_CLOUD_SSECURITY] == "S"
    assert kwargs["data"][CONF_CLOUD_SERVICE_TOKEN] == "T"
    assert kwargs["data"][CONF_CLOUD_USER_ID] == "U"


def test_create_entry_skips_tokens_when_incomplete(hass):
    handler = _handler(hass)
    handler._user_input = {CONF_NAME: "Vacuum"}
    cloud = MagicMock()
    cloud.session_tokens = MagicMock(
        return_value={"ssecurity": "S", "service_token": None, "user_id": "U"}
    )
    handler._cloud = cloud
    with patch.object(handler, "async_create_entry", return_value={}) as create:
        handler._create_entry()
    _, kwargs = create.call_args
    assert CONF_CLOUD_SSECURITY not in kwargs["data"]
