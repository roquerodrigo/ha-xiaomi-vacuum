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

    from .data import CloudSessionTokens, XiaomiVacuumConfigEntry

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
    VACUUM_MODEL_PREFIX,
)
from .spec import get_spec

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
        if not self._has_full_session(tokens):
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
            failure = await self._async_load_devices()
            if failure is not None:
                return failure

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

    async def _async_load_devices(self) -> config_entries.ConfigFlowResult | None:
        """Populate the vacuum list from the account; a result means failure."""
        if self._cloud is None:
            return self.async_abort(reason="cloud_list_failed")
        try:
            # Fetch every device first (unfiltered) so we can give the user a
            # useful hint when the vacuum they expect is missing — usually a
            # wrong cloud region, or a device whose model does not match the
            # `xiaomi.vacuum.` prefix this integration recognises.
            all_devices = await self._cloud.async_list_devices()
        except XiaomiCloudAuthError:
            # A rejected session (reconfigure reusing an expired one) is not
            # fixed by "try again later" — get a fresh login instead. The
            # finished task of the previous login must be dropped first:
            # `async_step_qr` treats a done task as a completed scan and would
            # bounce straight back to discover in an endless loop.
            LOGGER.warning(
                "Cloud session rejected while listing devices; "
                "requesting a fresh QR login"
            )
            self._qr_task = None
            return await self.async_step_qr()
        except XiaomiCloudError as exc:
            LOGGER.warning("Failed to list devices: %s", exc)
            return self.async_abort(reason="cloud_list_failed")
        LOGGER.debug(
            "Cloud returned %d device(s): %s",
            len(all_devices),
            {d.model for d in all_devices},
        )
        self._devices = [
            d for d in all_devices if d.model.startswith(VACUUM_MODEL_PREFIX)
        ]
        if not self._devices:
            return self.async_abort(reason=self._missing_vacuum_reason(all_devices))
        return None

    @staticmethod
    def _missing_vacuum_reason(all_devices: list[XiaomiDeviceInfo]) -> str:
        """Pick the abort reason (and log a hint) when no vacuum was found."""
        if not all_devices:
            return "no_vacuum_found"
        # Devices exist on the account, but none is a recognised vacuum —
        # most likely the S20+/X20 Max lives on a different region than the
        # one selected, or the account only holds non-vacuum hardware.
        LOGGER.warning(
            "Found %d device(s) on this account but none matches the %r prefix. "
            "Models seen: %s. If your vacuum is missing, try a different cloud "
            "region (reconfigure flow) or check the device is paired to this "
            "Mi Home account.",
            len(all_devices),
            VACUUM_MODEL_PREFIX,
            sorted({d.model for d in all_devices}),
        )
        return "no_vacuum_in_account"

    async def _finalize(
        self, device: XiaomiDeviceInfo
    ) -> config_entries.ConfigFlowResult:
        """Validate the local connection (using cloud-supplied IP) and create entry."""
        await self.async_set_unique_id(device.mac or device.device_id)
        self._abort_if_device_conflict()

        if not device.local_ip:
            return self.async_abort(reason="no_local_ip")

        client = XiaomiVacuumApiClient(
            host=device.local_ip,
            token=device.token,
            spec=get_spec(device.model),
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
        # Drop any previous QR state first: on a failed refresh the stale image
        # and long-poll URL of an already-expired login session must not be
        # reused by the retry path.
        self._qr_image = None
        self._qr_lp_url = None
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
        if not self._has_full_session(tokens):
            return
        self._user_input[CONF_CLOUD_SSECURITY] = tokens["ssecurity"]
        self._user_input[CONF_CLOUD_SERVICE_TOKEN] = tokens["service_token"]
        self._user_input[CONF_CLOUD_USER_ID] = tokens["user_id"]

    @staticmethod
    def _has_full_session(tokens: CloudSessionTokens) -> bool:
        """Whether all three cloud session token fields are present."""
        return bool(
            tokens["ssecurity"] and tokens["service_token"] and tokens["user_id"]
        )

    def _create_entry(self) -> config_entries.ConfigFlowResult:
        self._persist_session_tokens()
        return self.async_create_entry(
            title=self._user_input[CONF_NAME],
            data=self._user_input,
        )
