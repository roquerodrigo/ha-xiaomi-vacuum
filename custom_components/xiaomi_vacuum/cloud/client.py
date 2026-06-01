"""Async-friendly Xiaomi cloud client (executor-backed)."""

from __future__ import annotations

import json
from functools import partial
from typing import TYPE_CHECKING

import aiohttp
import requests
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..const import LOGGER  # noqa: TID252
from .connector import _HTTP_OK, _XiaomiCloudConnector
from .errors import XiaomiCloudAuthError, XiaomiCloudError

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant

    from .device_info import XiaomiDeviceInfo


class XiaomiCloud:
    """Async-friendly wrapper around _XiaomiCloudConnector (executor-backed)."""

    def __init__(self, hass: HomeAssistant, country: str) -> None:
        """Initialize the cloud client (no network calls until login)."""
        self._hass = hass
        self._country = country
        self._connector = _XiaomiCloudConnector()
        self._device: XiaomiDeviceInfo | None = None
        self._logged_in = False
        self._fault_texts: dict[int, str] = {}
        self._fault_codes_seen: set[int] = set()

    @classmethod
    def from_session(
        cls,
        hass: HomeAssistant,
        country: str,
        ssecurity: str,
        service_token: str,
        user_id: str,
    ) -> XiaomiCloud:
        """Build a logged-in client from previously saved session tokens."""
        instance = cls(hass, country)
        instance._connector._ssecurity = ssecurity  # noqa: SLF001
        instance._connector._service_token = service_token  # noqa: SLF001
        instance._connector._user_id = user_id  # noqa: SLF001
        instance._logged_in = True
        return instance

    def session_tokens(self) -> dict[str, str | None]:
        """Expose the active session tokens for persistence in the config entry."""
        return {
            "ssecurity": self._connector._ssecurity,  # noqa: SLF001
            "service_token": self._connector._service_token,  # noqa: SLF001
            "user_id": self._connector._user_id,  # noqa: SLF001
        }

    async def async_qr_start(self) -> tuple[bytes, str, int]:
        """Start the QR login flow; returns (png_bytes, long_polling_url, timeout_s)."""
        return await self._run(self._connector.start_qr_login)

    async def async_qr_login(
        self, long_polling_url: str, wait_seconds: int = 300
    ) -> None:
        """
        Wait for the user to scan the QR; sets session tokens on success.

        Uses native aiohttp for the long-poll so the task can be cancelled
        cleanly on HA shutdown — a sync request in an executor thread blocks
        the interpreter's exit until the 5-minute timeout fires.
        """
        ok = await self._async_poll_qr_login(long_polling_url, wait_seconds)
        if not ok:
            msg = "QR code not scanned in time (or login failed)"
            raise XiaomiCloudAuthError(msg)
        self._logged_in = True

    async def _async_poll_qr_login(  # noqa: PLR0911
        self,
        long_polling_url: str,
        timeout: int,  # noqa: ASYNC109
    ) -> bool:
        session = async_get_clientsession(self._hass)
        read_timeout = aiohttp.ClientTimeout(total=max(timeout + 15, 30))
        try:
            async with session.get(
                long_polling_url, timeout=read_timeout, allow_redirects=False
            ) as resp:
                if resp.status != _HTTP_OK:
                    LOGGER.debug("QR long-poll status %s", resp.status)
                    return False
                text = await resp.text()
        except (TimeoutError, aiohttp.ClientError) as exc:
            LOGGER.debug("QR long-poll failed: %s", exc)
            return False

        body = json.loads(text.replace("&&&START&&&", ""))
        if "ssecurity" not in body:
            LOGGER.debug("QR long-poll returned without ssecurity: %s", body)
            return False
        connector = self._connector
        connector._ssecurity = body["ssecurity"]  # noqa: SLF001
        connector._user_id = str(body["userId"])  # noqa: SLF001
        location = body.get("location")
        if not location:
            return False

        try:
            async with session.get(
                location, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != _HTTP_OK:
                    return False
                token_cookie = resp.cookies.get("serviceToken")
        except (TimeoutError, aiohttp.ClientError) as exc:
            LOGGER.debug("Service-token fetch failed: %s", exc)
            return False
        if not token_cookie:
            return False
        connector._service_token = token_cookie.value  # noqa: SLF001
        return True

    async def async_resolve_device(self, token: str) -> XiaomiDeviceInfo:
        """Find the vacuum in the cloud account and cache it on this client."""
        device = await self._run(self._connector.find_device, token, self._country)
        if device is None:
            msg = f"Device with token {token[:6]}… not found in cloud"
            raise XiaomiCloudError(msg)
        self._device = device
        LOGGER.debug(
            "Cloud-resolved device: model=%s did=%s",
            device.model,
            device.device_id,
        )
        return device

    async def async_list_devices(
        self, model_prefix: str = ""
    ) -> list[XiaomiDeviceInfo]:
        """Enumerate every device in the account whose model starts with prefix."""
        devices = await self._run(
            lambda: list(self._connector._iter_devices(self._country))  # noqa: SLF001
        )
        if not model_prefix:
            return devices
        return [d for d in devices if d.model.startswith(model_prefix)]

    async def async_get_map_bytes(self, map_obj_name: str) -> bytes | None:
        """Resolve map_obj_name → URL → binary blob."""
        if not self._logged_in or not self._device:
            return None
        url = await self._run(
            self._connector.get_map_url, self._device.country, map_obj_name
        )
        if not url:
            return None
        return await self._run(self._connector.get_map_bytes, url)

    async def async_fault_text(self, code: int) -> str | None:
        """
        Return the localized text for a fault `code`, or None if unknown.

        Results are cached per code; the cloud message feed is only queried
        when a code we have not seen before appears. A code with no matching
        message is not re-queried within the session.
        """
        if not self._logged_in or not self._device or not code:
            return None
        # Query the feed once per code so an unmatched fault doesn't re-hit
        # the cloud on every poll.
        if code not in self._fault_codes_seen:
            try:
                texts = await self._run(
                    self._connector.get_device_fault_texts,
                    self._device.country,
                    self._device.device_id,
                )
            except (requests.RequestException, XiaomiCloudError, ValueError) as exc:
                LOGGER.debug("Failed to fetch fault texts: %s", exc)
                return None
            self._fault_texts.update(texts)
            self._fault_codes_seen.add(int(code))
        return self._fault_texts.get(int(code))

    async def _run[T, **P](
        self, func: Callable[P, T], *args: P.args, **kwargs: P.kwargs
    ) -> T:
        return await self._hass.async_add_executor_job(partial(func, *args, **kwargs))
