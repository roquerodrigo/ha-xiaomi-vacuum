"""Config flow for Xiaomi Vacuum (cloud-discovery via QR login)."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries

from .api import (
    XiaomiVacuumApiClient,
    XiaomiVacuumApiClientCommunicationError,
    XiaomiVacuumApiClientError,
)
from .cloud import (
    XiaomiCloud,
    XiaomiCloudAuthError,
    XiaomiCloudError,
    XiaomiDeviceInfo,
)

if TYPE_CHECKING:
    import asyncio
from .const import (
    CONF_CLOUD_COUNTRY,
    CONF_CLOUD_SERVICE_TOKEN,
    CONF_CLOUD_SSECURITY,
    CONF_CLOUD_USER_ID,
    CONF_HOST,
    CONF_NAME,
    CONF_TOKEN,
    DOMAIN,
    LOGGER,
)

_VACUUM_MODEL_PREFIX = "xiaomi.vacuum."
_DEVICE_PICK = "device"
_CLOUD_COUNTRY = "us"


class XiaomiVacuumFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Cloud-first config flow: pick region → scan QR → pick vacuum → done."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize transient state for the multi-step flow."""
        super().__init__()
        self._user_input: dict[str, Any] = {}
        self._cloud: XiaomiCloud | None = None
        self._qr_image: bytes | None = None
        self._qr_lp_url: str | None = None
        self._qr_timeout: int = 300
        self._qr_task: asyncio.Task | None = None
        self._devices: list[XiaomiDeviceInfo] = []

    async def async_step_user(
        self,
        user_input: dict | None = None,  # noqa: ARG002
    ) -> config_entries.ConfigFlowResult:
        """Skip straight to the QR step; cloud region is hard-coded."""
        self._user_input = {CONF_CLOUD_COUNTRY: _CLOUD_COUNTRY}
        return await self.async_step_qr()

    async def async_step_qr(
        self,
        user_input: dict | None = None,  # noqa: ARG002
    ) -> config_entries.ConfigFlowResult:
        """Show QR + run a single long-poll in background until the user scans it."""
        if self._qr_task is None:
            await self._refresh_qr()
            self._qr_task = self.hass.async_create_task(
                self._cloud.async_qr_login(
                    self._qr_lp_url, wait_seconds=self._qr_timeout
                )
            )

        if not self._qr_task.done():
            return self.async_show_progress(
                step_id="qr",
                progress_action="waiting_for_scan",
                description_placeholders={"qr_image": self._qr_data_uri()},
                progress_task=self._qr_task,
            )

        try:
            self._qr_task.result()
        except XiaomiCloudAuthError:
            self._qr_task = None
            return self.async_show_progress_done(next_step_id="qr_failed")
        except XiaomiCloudError as exc:
            LOGGER.warning("Cloud login failed: %s", exc)
            self._qr_task = None
            return self.async_show_progress_done(next_step_id="qr_failed")
        return self.async_show_progress_done(next_step_id="discover")

    async def async_step_qr_failed(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show retry form after a QR timeout / scan failure."""
        if user_input is not None:
            return await self.async_step_qr()
        return self.async_show_form(
            step_id="qr_failed",
            data_schema=vol.Schema({}),
            errors={"base": "qr_not_scanned"},
        )

    async def async_step_discover(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """List vacuums in the account; auto-pick if there's exactly one."""
        if not self._devices:
            try:
                self._devices = await self._cloud.async_list_devices(
                    model_prefix=_VACUUM_MODEL_PREFIX
                )
            except XiaomiCloudError as exc:
                LOGGER.warning("Failed to list devices: %s", exc)
                return self.async_abort(reason="cloud_list_failed")
            if not self._devices:
                return self.async_abort(reason="no_vacuum_found")

        if len(self._devices) == 1:
            return await self._finalize(self._devices[0])

        if user_input is not None:
            chosen = next(
                (d for d in self._devices if d.device_id == user_input[_DEVICE_PICK]),
                None,
            )
            if chosen is not None:
                return await self._finalize(chosen)

        options = {
            d.device_id: f"{d.name} ({d.model}) — {d.local_ip or '?'}"
            for d in self._devices
        }
        return self.async_show_form(
            step_id="discover",
            data_schema=vol.Schema({vol.Required(_DEVICE_PICK): vol.In(options)}),
        )

    async def _finalize(
        self, device: XiaomiDeviceInfo
    ) -> config_entries.ConfigFlowResult:
        """Validate the local connection (using cloud-supplied IP) and create entry."""
        await self.async_set_unique_id(device.mac or device.device_id)
        self._abort_if_unique_id_configured()

        if not device.local_ip:
            return self.async_abort(reason="no_local_ip")

        client = XiaomiVacuumApiClient(
            hass=self.hass, host=device.local_ip, token=device.token
        )
        try:
            info = await client.async_get_info()
        except XiaomiVacuumApiClientCommunicationError as exc:
            LOGGER.error("Cannot reach %s: %s", device.local_ip, exc)
            return self.async_abort(reason="local_unreachable")
        except XiaomiVacuumApiClientError as exc:
            LOGGER.exception("Local probe failed: %s", exc)
            return self.async_abort(reason="local_probe_failed")

        mac = getattr(info, "mac_address", None) or device.mac
        if mac and mac != self.unique_id:
            await self.async_set_unique_id(mac, raise_on_progress=False)
            self._abort_if_unique_id_configured()

        self._user_input.update(
            {
                CONF_HOST: device.local_ip,
                CONF_TOKEN: device.token,
                CONF_NAME: device.name,
            }
        )
        return self._create_entry()

    async def _refresh_qr(self) -> None:
        """Get a new QR image + long-polling URL."""
        if self._cloud is None:
            self._cloud = XiaomiCloud(
                self.hass, country=self._user_input[CONF_CLOUD_COUNTRY]
            )
        try:
            qr, lp, timeout = await self._cloud.async_qr_start()
        except XiaomiCloudError as exc:
            LOGGER.warning("Failed to start QR login: %s", exc)
            return
        self._qr_image = qr
        self._qr_lp_url = lp
        self._qr_timeout = timeout

    def _qr_data_uri(self) -> str:
        if not self._qr_image:
            return ""
        return f"data:image/png;base64,{base64.b64encode(self._qr_image).decode()}"

    def _create_entry(self) -> config_entries.ConfigFlowResult:
        if self._cloud is not None:
            tokens = self._cloud.session_tokens()
            if tokens["ssecurity"] and tokens["service_token"] and tokens["user_id"]:
                self._user_input[CONF_CLOUD_SSECURITY] = tokens["ssecurity"]
                self._user_input[CONF_CLOUD_SERVICE_TOKEN] = tokens["service_token"]
                self._user_input[CONF_CLOUD_USER_ID] = tokens["user_id"]
        return self.async_create_entry(
            title=self._user_input[CONF_NAME],
            data=self._user_input,
        )
