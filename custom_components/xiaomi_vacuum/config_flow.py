"""Config flow for Xiaomi Vacuum (cloud-discovery via QR login)."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

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
    from collections.abc import Mapping

    from homeassistant.helpers.typing import ConfigType

    from .data import XiaomiVacuumConfigEntry

from .const import (
    CLOUD_REGIONS,
    CONF_CLOUD_COUNTRY,
    CONF_CLOUD_SERVICE_TOKEN,
    CONF_CLOUD_SSECURITY,
    CONF_CLOUD_USER_ID,
    CONF_HOST,
    CONF_NAME,
    CONF_TOKEN,
    DEFAULT_CLOUD_REGION,
    DOMAIN,
    LOGGER,
)

_VACUUM_MODEL_PREFIX = "xiaomi.vacuum."
_DEVICE_PICK = "device"


class XiaomiVacuumFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """
    Cloud-first config flow: pick region → scan QR → pick vacuum → done.

    Supports reauth (refresh the cloud session) and reconfigure (switch the
    cloud region of an existing entry, reusing its stored session).
    """

    VERSION = 1

    def __init__(self) -> None:
        """Initialize transient state for the multi-step flow."""
        super().__init__()
        self._user_input: ConfigType = {}
        self._cloud: XiaomiCloud | None = None
        self._qr_image: bytes | None = None
        self._qr_lp_url: str | None = None
        self._qr_timeout: int = 300
        self._qr_task: asyncio.Task[None] | None = None
        self._devices: list[XiaomiDeviceInfo] = []
        self._reauth_entry: XiaomiVacuumConfigEntry | None = None
        self._reconfigure_entry: XiaomiVacuumConfigEntry | None = None

    def _region_schema(self, default: str) -> vol.Schema:
        """Build the region-picker schema, preselecting `default`."""
        return vol.Schema(
            {
                vol.Required(CONF_CLOUD_COUNTRY, default=default): SelectSelector(
                    SelectSelectorConfig(
                        options=list(CLOUD_REGIONS),
                        translation_key="cloud_country",
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )

    async def async_step_user(
        self,
        user_input: ConfigType | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Pick the Xiaomi cloud region, then advance to the QR step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=self._region_schema(DEFAULT_CLOUD_REGION),
            )
        self._user_input = {CONF_CLOUD_COUNTRY: user_input[CONF_CLOUD_COUNTRY]}
        return await self.async_step_qr()

    async def async_step_reconfigure(
        self,
        user_input: ConfigType | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Change the cloud region of an existing entry, reusing its session."""
        entry = self._get_reconfigure_entry()
        self._reconfigure_entry = entry
        if user_input is None:
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=self._region_schema(entry.data[CONF_CLOUD_COUNTRY]),
            )
        self._user_input = {CONF_CLOUD_COUNTRY: user_input[CONF_CLOUD_COUNTRY]}
        self._cloud = XiaomiCloud.from_session(
            self.hass,
            country=user_input[CONF_CLOUD_COUNTRY],
            ssecurity=entry.data[CONF_CLOUD_SSECURITY],
            service_token=entry.data[CONF_CLOUD_SERVICE_TOKEN],
            user_id=entry.data[CONF_CLOUD_USER_ID],
        )
        return await self.async_step_discover()

    async def async_step_reauth(
        self,
        entry_data: Mapping[str, str],  # noqa: ARG002
    ) -> config_entries.ConfigFlowResult:
        """Handle re-auth started when the saved cloud session expired."""
        self._reauth_entry = self._get_reauth_entry()
        self._user_input = {
            CONF_CLOUD_COUNTRY: self._reauth_entry.data[CONF_CLOUD_COUNTRY]
        }
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: ConfigType | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Confirm, then show a fresh QR to refresh the cloud session."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm", data_schema=vol.Schema({})
            )
        return await self.async_step_qr()

    async def async_step_reauth_finish(
        self,
        user_input: ConfigType | None = None,  # noqa: ARG002
    ) -> config_entries.ConfigFlowResult:
        """Persist the refreshed cloud tokens onto the existing entry."""
        entry = self._reauth_entry
        if entry is None or self._cloud is None:
            return self.async_abort(reason="reauth_failed")
        tokens = self._cloud.session_tokens()
        if not (tokens["ssecurity"] and tokens["service_token"] and tokens["user_id"]):
            return self.async_abort(reason="reauth_failed")
        return self.async_update_reload_and_abort(
            entry,
            data={
                **entry.data,
                CONF_CLOUD_SSECURITY: tokens["ssecurity"],
                CONF_CLOUD_SERVICE_TOKEN: tokens["service_token"],
                CONF_CLOUD_USER_ID: tokens["user_id"],
            },
        )

    async def async_step_qr(
        self,
        user_input: ConfigType | None = None,  # noqa: ARG002
    ) -> config_entries.ConfigFlowResult:
        """Show QR + run a single long-poll in background until the user scans it."""
        if self._qr_task is None:
            await self._refresh_qr()
            if self._cloud is None or self._qr_lp_url is None:
                return self.async_show_progress_done(next_step_id="qr_failed")
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
        next_step = "reauth_finish" if self._reauth_entry is not None else "discover"
        return self.async_show_progress_done(next_step_id=next_step)

    async def async_step_qr_failed(
        self, user_input: ConfigType | None = None
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
        user_input: ConfigType | None = None,
    ) -> config_entries.ConfigFlowResult:
        """List vacuums in the account; auto-pick if there's exactly one."""
        if not self._devices:
            if self._cloud is None:
                return self.async_abort(reason="cloud_list_failed")
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
        self._abort_if_device_conflict()

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
            self._abort_if_device_conflict()

        self._user_input.update(
            {
                CONF_HOST: device.local_ip,
                CONF_TOKEN: device.token,
                CONF_NAME: device.name,
                CONF_CLOUD_COUNTRY: device.country,
            }
        )
        if self._reconfigure_entry is not None:
            self._persist_session_tokens()
            return self.async_update_reload_and_abort(
                self._reconfigure_entry,
                data={**self._reconfigure_entry.data, **self._user_input},
            )
        return self._create_entry()

    def _abort_if_device_conflict(self) -> None:
        """Reject a duplicate device (setup) or the wrong device (reconfigure)."""
        if self._reconfigure_entry is not None:
            self._abort_if_unique_id_mismatch()
        else:
            self._abort_if_unique_id_configured()

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

    def _persist_session_tokens(self) -> None:
        """Copy the live cloud session tokens into `_user_input` when complete."""
        if self._cloud is None:
            return
        tokens = self._cloud.session_tokens()
        if tokens["ssecurity"] and tokens["service_token"] and tokens["user_id"]:
            self._user_input[CONF_CLOUD_SSECURITY] = tokens["ssecurity"]
            self._user_input[CONF_CLOUD_SERVICE_TOKEN] = tokens["service_token"]
            self._user_input[CONF_CLOUD_USER_ID] = tokens["user_id"]

    def _create_entry(self) -> config_entries.ConfigFlowResult:
        self._persist_session_tokens()
        return self.async_create_entry(
            title=self._user_input[CONF_NAME],
            data=self._user_input,
        )
