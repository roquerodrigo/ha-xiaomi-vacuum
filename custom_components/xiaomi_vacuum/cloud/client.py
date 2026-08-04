"""Async-friendly Xiaomi cloud client (executor-backed)."""

from __future__ import annotations

import json
import re
from functools import partial
from typing import TYPE_CHECKING

import aiohttp
import requests
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from ..const import LOGGER  # noqa: TID252
from .connector import _HTTP_OK, _XiaomiCloudConnector
from .errors import (
    XiaomiCloudAuthError,
    XiaomiCloudConnectionError,
    XiaomiCloudError,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant

    from ..data import CloudSessionTokens, JsonValue  # noqa: TID252
    from .device_info import XiaomiDeviceInfo

_URL_QUERY_STRING = re.compile(r"\?\S*")


def _sanitized_error_text(exception: Exception) -> str:
    """
    Strip URL query strings from upstream error text before it can be logged.

    requests/urllib3 embed the full request URL in their exception messages,
    and the signed cloud calls carry the plaintext ``ssecurity`` session secret
    as a query parameter — without this, a routine connection failure would
    write the credential into Home Assistant's log.
    """
    return _URL_QUERY_STRING.sub("?<redacted>", str(exception))


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

    def session_tokens(self) -> CloudSessionTokens:
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

    async def _async_poll_qr_login(
        self,
        long_polling_url: str,
        timeout: int,  # noqa: ASYNC109
    ) -> bool:
        # A dedicated session (own cookie jar) keeps the Xiaomi account cookies
        # set during login out of Home Assistant's shared client session, where
        # any integration hitting a Xiaomi domain would silently replay them.
        session = async_create_clientsession(self._hass)
        try:
            return await self._async_poll_qr_login_in_session(
                session, long_polling_url, timeout
            )
        finally:
            await session.close()

    async def _async_poll_qr_login_in_session(  # noqa: PLR0911
        self,
        session: aiohttp.ClientSession,
        long_polling_url: str,
        timeout: int,  # noqa: ASYNC109
    ) -> bool:
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

        try:
            body = json.loads(text.replace("&&&START&&&", ""))
        except ValueError:
            LOGGER.debug("QR long-poll returned a non-JSON body")
            return False
        if not isinstance(body, dict) or "ssecurity" not in body:
            LOGGER.debug("QR long-poll returned without ssecurity: %s", body)
            return False
        user_id = body.get("userId")
        if user_id is None:
            LOGGER.debug("QR long-poll returned without userId: %s", body)
            return False
        connector = self._connector
        connector._ssecurity = body["ssecurity"]  # noqa: SLF001
        connector._user_id = str(user_id)  # noqa: SLF001
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

    async def async_call_action(
        self, siid: int, aiid: int, params: list[str] | None = None
    ) -> dict[str, JsonValue] | None:
        """
        Invoke a MIoT action through the cloud (reliable TCP).

        Used as the transport for multi-step flows that local UDP mishandles
        (notably the S20+ room-clean, where ``set-room-clean-configs`` +
        ``start-custom-sweep`` routinely time out locally with ``-9999``). The
        Mi Home app uses this same cloud path.
        """
        if not self._logged_in or not self._device:
            return None
        return await self._run(
            self._connector.call_action,
            self._device.country,
            self._device.device_id,
            siid,
            aiid,
            params,
        )

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
            except XiaomiCloudError as exc:
                LOGGER.debug("Failed to fetch fault texts: %s", exc)
                return None
            self._fault_texts.update(texts)
            self._fault_codes_seen.add(int(code))
        return self._fault_texts.get(int(code))

    async def _run[T, **P](
        self, func: Callable[P, T], *args: P.args, **kwargs: P.kwargs
    ) -> T:
        try:
            return await self._hass.async_add_executor_job(
                partial(func, *args, **kwargs)
            )
        except requests.RequestException as exception:
            msg = f"Cannot reach the Xiaomi cloud: {_sanitized_error_text(exception)}"
            raise XiaomiCloudConnectionError(msg) from exception
        except ValueError as exception:
            # A 200 response whose body is not decodable/parsable (proxy or
            # captive-portal page, truncated body, session desync) surfaces as
            # base64/JSON ValueErrors — infrastructure trouble, not a bug.
            msg = f"Malformed response from the Xiaomi cloud: {exception}"
            raise XiaomiCloudConnectionError(msg) from exception
