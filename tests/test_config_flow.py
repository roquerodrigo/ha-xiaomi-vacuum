from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.xiaomi_vacuum.cloud import XiaomiDeviceInfo
from custom_components.xiaomi_vacuum.config_flow import XiaomiVacuumFlowHandler
from custom_components.xiaomi_vacuum.const import (
    CONF_CLOUD_COUNTRY,
    CONF_CLOUD_SERVICE_TOKEN,
    CONF_CLOUD_SSECURITY,
    CONF_CLOUD_USER_ID,
    CONF_DEVICE_INFO,
    CONF_HOST,
    CONF_NAME,
    CONF_TOKEN,
    DOMAIN,
)


async def _start(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


def _device(
    device_id="d1", local_ip="192.168.1.5", mac="AA:BB:CC:DD:EE:FF", country="us"
):
    return XiaomiDeviceInfo(
        device_id=device_id,
        name="Vacuum",
        model="xiaomi.vacuum.d109gl",
        token="abc",
        country=country,
        local_ip=local_ip,
        mac=mac,
    )


def _handler(hass):
    handler = XiaomiVacuumFlowHandler()
    handler.hass = hass
    return handler


async def test_step_user_shows_region_form(hass, enable_custom_integrations):
    """Add Hub → region picker form before anything else."""
    result = await _start(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_region_selection_starts_qr_progress(hass, enable_custom_integrations):
    """Picking a region builds the cloud client for it and shows the QR dialog."""
    cloud = MagicMock()
    cloud.async_qr_start = AsyncMock(return_value=(b"PNG", "https://lp", 60))

    pending = asyncio.Future()

    async def hang(*_a, **_kw):
        return await pending

    cloud.async_qr_login = hang

    with patch(
        "custom_components.xiaomi_vacuum.config_flow.XiaomiCloud", return_value=cloud
    ) as cloud_cls:
        try:
            start = await _start(hass)
            result = await hass.config_entries.flow.async_configure(
                start["flow_id"], {CONF_CLOUD_COUNTRY: "de"}
            )
            assert result["type"] == FlowResultType.SHOW_PROGRESS
            assert result["step_id"] == "qr"
            assert result["progress_action"] == "waiting_for_scan"
            assert (
                "data:image/png;base64,"
                in result["description_placeholders"]["qr_image"]
            )
            _, kwargs = cloud_cls.call_args
            assert kwargs["country"] == "de"
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


async def test_refresh_qr_clears_stale_state_on_failure(hass):
    """A failed refresh must not leave an expired QR image/long-poll URL behind."""
    from custom_components.xiaomi_vacuum.cloud import XiaomiCloudError

    handler = _handler(hass)
    cloud = MagicMock()
    cloud.async_qr_start = AsyncMock(side_effect=XiaomiCloudError("nope"))
    handler._cloud = cloud
    handler._qr_image = b"EXPIRED"
    handler._qr_lp_url = "https://expired-lp"
    await handler._refresh_qr()
    assert handler._qr_image is None
    assert handler._qr_lp_url is None


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


async def test_qr_step_proceeds_to_reauth_finish_when_reauthing(hass):
    handler = _handler(hass)
    handler._reauth_entry = MagicMock()
    task = MagicMock()
    task.done.return_value = True
    task.result.return_value = None
    handler._qr_task = task
    result = await handler.async_step_qr()
    assert result["step_id"] == "reauth_finish"


async def test_reauth_stores_entry_and_confirms(hass):
    handler = _handler(hass)
    entry = MagicMock()
    entry.data = {CONF_CLOUD_COUNTRY: "de"}
    with (
        patch.object(handler, "_get_reauth_entry", return_value=entry),
        patch.object(
            handler,
            "async_step_reauth_confirm",
            AsyncMock(return_value={"type": "form"}),
        ) as confirm,
    ):
        result = await handler.async_step_reauth({})
    assert handler._reauth_entry is entry
    # Region comes from the existing entry, not a hard-coded default.
    assert handler._user_input[CONF_CLOUD_COUNTRY] == "de"
    confirm.assert_awaited_once()
    assert result == {"type": "form"}


async def test_reauth_confirm_shows_form(hass):
    handler = _handler(hass)
    result = await handler.async_step_reauth_confirm()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"


async def test_reauth_confirm_input_starts_qr(hass):
    handler = _handler(hass)
    with patch.object(
        handler, "async_step_qr", AsyncMock(return_value={"type": "progress"})
    ) as qr:
        result = await handler.async_step_reauth_confirm(user_input={})
    qr.assert_awaited_once()
    assert result == {"type": "progress"}


async def test_reauth_finish_persists_tokens_onto_entry(hass):
    handler = _handler(hass)
    entry = MagicMock()
    entry.data = {CONF_HOST: "192.168.1.5", CONF_TOKEN: "abc"}
    handler._reauth_entry = entry
    cloud = MagicMock()
    cloud.session_tokens = MagicMock(
        return_value={"ssecurity": "S", "service_token": "T", "user_id": "U"}
    )
    handler._cloud = cloud
    aborted = {"type": FlowResultType.ABORT, "reason": "reauth_successful"}
    with patch.object(
        handler, "async_update_reload_and_abort", return_value=aborted
    ) as upd:
        result = await handler.async_step_reauth_finish()
    assert result is aborted
    args, kwargs = upd.call_args
    assert args[0] is entry
    assert kwargs["data"][CONF_CLOUD_SSECURITY] == "S"
    assert kwargs["data"][CONF_CLOUD_SERVICE_TOKEN] == "T"
    assert kwargs["data"][CONF_CLOUD_USER_ID] == "U"
    assert kwargs["data"][CONF_HOST] == "192.168.1.5"
    assert kwargs["data"][CONF_TOKEN] == "abc"


async def test_reauth_finish_aborts_without_entry(hass):
    handler = _handler(hass)
    handler._reauth_entry = None
    handler._cloud = MagicMock()
    result = await handler.async_step_reauth_finish()
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_failed"


async def test_reauth_finish_aborts_on_incomplete_tokens(hass):
    handler = _handler(hass)
    handler._reauth_entry = MagicMock(data={})
    cloud = MagicMock()
    cloud.session_tokens = MagicMock(
        return_value={"ssecurity": "S", "service_token": None, "user_id": "U"}
    )
    handler._cloud = cloud
    result = await handler.async_step_reauth_finish()
    assert result["reason"] == "reauth_failed"


async def test_reconfigure_shows_region_form(hass):
    handler = _handler(hass)
    entry = MagicMock()
    entry.data = {CONF_CLOUD_COUNTRY: "us"}
    with patch.object(handler, "_get_reconfigure_entry", return_value=entry):
        result = await handler.async_step_reconfigure()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert handler._reconfigure_entry is entry


async def test_reconfigure_reuses_session_and_discovers(hass):
    handler = _handler(hass)
    entry = MagicMock()
    entry.data = {
        CONF_CLOUD_COUNTRY: "us",
        CONF_CLOUD_SSECURITY: "S",
        CONF_CLOUD_SERVICE_TOKEN: "T",
        CONF_CLOUD_USER_ID: "U",
    }
    cloud = MagicMock()
    with (
        patch.object(handler, "_get_reconfigure_entry", return_value=entry),
        patch(
            "custom_components.xiaomi_vacuum.config_flow.XiaomiCloud.from_session",
            return_value=cloud,
        ) as from_session,
        patch.object(
            handler, "async_step_discover", AsyncMock(return_value={"type": "form"})
        ) as discover,
    ):
        result = await handler.async_step_reconfigure(
            user_input={CONF_CLOUD_COUNTRY: "de"}
        )
    _, kwargs = from_session.call_args
    assert kwargs["country"] == "de"
    assert kwargs["ssecurity"] == "S"
    assert kwargs["service_token"] == "T"
    assert kwargs["user_id"] == "U"
    assert handler._cloud is cloud
    assert handler._user_input[CONF_CLOUD_COUNTRY] == "de"
    discover.assert_awaited_once()
    assert result == {"type": "form"}


async def test_discover_routes_to_qr_when_session_rejected(hass):
    """An expired session must request a fresh login, not tell the user to retry."""
    from custom_components.xiaomi_vacuum.cloud import XiaomiCloudAuthError

    handler = _handler(hass)
    cloud = MagicMock()
    cloud.async_list_devices = AsyncMock(side_effect=XiaomiCloudAuthError("401"))
    handler._cloud = cloud
    with patch.object(
        handler, "async_step_qr", AsyncMock(return_value={"type": "qr"})
    ) as step_qr:
        result = await handler.async_step_discover()
    step_qr.assert_awaited_once()
    assert result == {"type": "qr"}


async def test_finalize_updates_entry_on_reconfigure(hass):
    handler = _handler(hass)
    entry = MagicMock()
    entry.data = {
        CONF_CLOUD_COUNTRY: "us",
        CONF_CLOUD_SSECURITY: "S",
        CONF_CLOUD_SERVICE_TOKEN: "T",
        CONF_CLOUD_USER_ID: "U",
        CONF_DEVICE_INFO: {"model": "x"},
    }
    handler._reconfigure_entry = entry
    handler._user_input = {}
    handler.async_set_unique_id = AsyncMock(return_value=None)
    handler._abort_if_unique_id_mismatch = MagicMock(return_value=None)
    cloud = MagicMock()
    cloud.session_tokens = MagicMock(
        return_value={"ssecurity": "S", "service_token": "T", "user_id": "U"}
    )
    handler._cloud = cloud

    info = MagicMock()
    info.mac_address = "AA:BB:CC:DD:EE:FF"
    client = MagicMock()
    client.async_get_info = AsyncMock(return_value=info)
    updated = {"type": FlowResultType.ABORT, "reason": "reconfigure_successful"}
    with (
        patch(
            "custom_components.xiaomi_vacuum.config_flow.XiaomiVacuumApiClient",
            return_value=client,
        ),
        patch.object(
            handler, "async_update_reload_and_abort", return_value=updated
        ) as upd,
        patch.object(
            type(handler), "unique_id", new_callable=lambda: "AA:BB:CC:DD:EE:FF"
        ),
    ):
        result = await handler._finalize(_device(country="de"))
    assert result is updated
    args, kwargs = upd.call_args
    assert args[0] is entry
    # New region persisted; existing entry data (device_info) preserved.
    assert kwargs["data"][CONF_CLOUD_COUNTRY] == "de"
    assert kwargs["data"][CONF_DEVICE_INFO] == {"model": "x"}
    assert kwargs["data"][CONF_HOST] == "192.168.1.5"
    handler._abort_if_unique_id_mismatch.assert_called()


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


async def test_discover_aborts_no_vacuum_in_account_when_only_non_vacuums(hass):
    """Devices exist but none matches the xiaomi.vacuum. prefix."""
    handler = _handler(hass)
    cloud = MagicMock()
    lamp = XiaomiDeviceInfo(
        device_id="l1", name="Lamp", model="yeelink.light.1", token="x", country="us"
    )
    cloud.async_list_devices = AsyncMock(return_value=[lamp])
    handler._cloud = cloud
    result = await handler.async_step_discover()
    assert result["reason"] == "no_vacuum_in_account"


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
    # Region is persisted from the resolved device, not the picker default.
    assert handler._user_input[CONF_CLOUD_COUNTRY] == "us"


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
