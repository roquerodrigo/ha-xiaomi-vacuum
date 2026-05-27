"""Xiaomi Cloud client — QR Code login + map fetch (no password/CAPTCHA/2FA)."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import random
import time
from functools import partial
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, NamedTuple

import aiohttp
import requests
from Crypto.Cipher import ARC4
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import LOGGER

if TYPE_CHECKING:
    from collections.abc import Iterator

    from homeassistant.core import HomeAssistant

_HTTP_OK = int(HTTPStatus.OK)
_QR_DEFAULT_LOCALE = "en_US"


class XiaomiDeviceInfo(NamedTuple):
    """A single device discovered in the Xiaomi cloud account."""

    device_id: str
    name: str
    model: str
    token: str
    country: str
    local_ip: str | None = None
    mac: str | None = None


class XiaomiCloudError(Exception):
    """Generic cloud error."""


class XiaomiCloudAuthError(XiaomiCloudError):
    """Authentication failed (login expired, QR not scanned, etc.)."""


class _XiaomiCloudConnector:
    """Sync client for the Xiaomi cloud — QR login + signed MIoT calls."""

    def __init__(self) -> None:
        """Initialize a fresh session with the standard SDK cookies."""
        self._agent = self._gen_agent()
        self._device_id = self._gen_device_id()
        self._session = requests.session()
        for domain in ("mi.com", "xiaomi.com"):
            self._session.cookies.set("sdkVersion", "accountsdk-18.8.15", domain=domain)
            self._session.cookies.set("deviceId", self._device_id, domain=domain)
        self._ssecurity: str | None = None
        self._user_id: str | None = None
        self._service_token: str | None = None

    def start_qr_login(self) -> tuple[bytes, str, int]:
        """Request a fresh QR code; returns (png_bytes, long_polling_url, timeout_s)."""
        params = {
            "_qrsize": "240",
            "qs": "%3Fsid%3Dxiaomiio%26_json%3Dtrue",
            "callback": "https://sts.api.io.mi.com/sts",
            "_hasLogo": "false",
            "sid": "xiaomiio",
            "serviceParam": "",
            "_locale": _QR_DEFAULT_LOCALE,
            "_dc": str(int(time.time() * 1000)),
        }
        response = self._session.get(
            "https://account.xiaomi.com/longPolling/loginUrl",
            params=params,
            timeout=10,
        )
        body = self._to_json(response.text)
        qr_bytes = self._session.get(body["qr"], timeout=10).content
        return qr_bytes, body["lp"], int(body.get("timeout", 60))

    def poll_qr_login(self, long_polling_url: str, timeout: int) -> bool:
        """
        Single long-poll: server holds the connection until the user scans.

        Reconnecting in a tight loop is treated as abuse by Xiaomi and silently
        fails — the official web flow does exactly one GET with a long read
        timeout (~315s) and waits.
        """
        read_timeout = max(timeout + 15, 30)
        try:
            response = self._session.get(long_polling_url, timeout=read_timeout)
        except (requests.Timeout, requests.RequestException) as exc:
            LOGGER.debug("QR long-poll failed: %s", exc)
            return False
        if response.status_code != _HTTP_OK:
            LOGGER.debug(
                "QR long-poll status %s: %s", response.status_code, response.text[:200]
            )
            return False
        body = self._to_json(response.text)
        if "ssecurity" not in body:
            LOGGER.debug("QR long-poll returned without ssecurity: %s", body)
            return False
        self._ssecurity = body["ssecurity"]
        self._user_id = str(body["userId"])
        location = body.get("location")
        if not location:
            return False
        return self._fetch_service_token(location)

    def _fetch_service_token(self, location: str) -> bool:
        response = self._session.get(
            location,
            headers={"content-type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        if response.status_code != _HTTP_OK:
            return False
        token = response.cookies.get("serviceToken")
        if not token:
            return False
        self._service_token = token
        return True

    def find_device(self, token: str, country: str) -> XiaomiDeviceInfo | None:
        """Locate a device by miIO token in the given country."""
        for device in self._iter_devices(country):
            if device.token.casefold() == token.casefold():
                return device
        return None

    def _iter_devices(self, country: str) -> Iterator[XiaomiDeviceInfo]:
        for home in self._iter_homes(country):
            yield from self._iter_home_devices(country, home["id"], home["uid"])

    def _iter_homes(self, country: str) -> Iterator[dict[str, Any]]:
        url = self._api_url(country) + "/v2/homeroom/gethome"
        params = {
            "data": json.dumps(
                {
                    "fg": True,
                    "fetch_share": True,
                    "fetch_share_dev": True,
                    "limit": 300,
                    "app_ver": 7,
                }
            )
        }
        response = self._encrypted_call(url, params)
        if not response or "result" not in response:
            return
        result = response["result"] or {}
        for key in ("homelist", "share_home_list"):
            for home in result.get(key) or []:
                yield {"id": int(home["id"]), "uid": home["uid"]}

    def _iter_home_devices(
        self, country: str, home_id: int, owner_id: int
    ) -> Iterator[XiaomiDeviceInfo]:
        url = self._api_url(country) + "/v2/home/home_device_list"
        params = {
            "data": json.dumps(
                {
                    "home_id": home_id,
                    "home_owner": owner_id,
                    "limit": 200,
                    "get_split_device": True,
                    "support_smart_home": True,
                }
            )
        }
        response = self._encrypted_call(url, params)
        if not response or not (result := response.get("result")):
            return
        for device in result.get("device_info") or []:
            yield XiaomiDeviceInfo(
                device_id=device["did"],
                name=device["name"],
                model=device["model"],
                token=device["token"],
                country=country,
                local_ip=device.get("localip") or device.get("local_ip"),
                mac=device.get("mac"),
            )

    def get_map_url(self, country: str, map_obj_name: str) -> str | None:
        """Resolve a `map-obj-name` (from MIoT) to a temporary HTTPS download URL."""
        params = {"data": json.dumps({"obj_name": map_obj_name})}
        # `_pro` is the only endpoint that works for d109gl; the non-_pro is kept
        # as a primary attempt for compatibility with other models.
        for endpoint in (
            "/v2/home/get_interim_file_url",
            "/v2/home/get_interim_file_url_pro",
        ):
            url = self._api_url(country) + endpoint
            response = self._encrypted_call(url, params)
            if response and (result := response.get("result")) and result.get("url"):
                return result["url"]
        return None

    def get_map_bytes(self, map_url: str) -> bytes | None:
        """Download the raw binary map from the temporary URL."""
        response = self._session.get(map_url, timeout=10)
        if response.status_code != _HTTP_OK:
            return None
        return response.content

    def get_device_fault_texts(
        self, country: str, did: str, limit: int = 50
    ) -> dict[int, str]:
        """
        Map fault codes to their localized text from the device message feed.

        The vacuum reports a fault as a numeric code on its `fault` property
        (siid 2 / piid 3). Xiaomi's cloud emits a localized push message
        (type 6) for each fault whose `params.body.value` carries that code and
        whose `title` is the human-readable text in the account's language.
        We read that feed and build `{code: title}`. `force_read` is kept false
        so we never alter the user's unread state.
        """
        url = self._api_url(country) + "/v2/message/v2/list"
        params = {
            "data": json.dumps(
                {
                    "did": str(did),
                    "type": 6,
                    "timestamp": 0,
                    "limit": limit,
                    "force_read": False,
                }
            )
        }
        response = self._encrypted_call(url, params)
        texts: dict[int, str] = {}
        if not response or not (result := response.get("result")):
            return texts
        for message in result.get("messages") or []:
            body = (message.get("params") or {}).get("body") or {}
            value = body.get("value") or body.get("extra") or []
            title = message.get("title")
            if title and isinstance(value, list) and value:
                try:
                    texts.setdefault(int(value[0]), title)
                except TypeError, ValueError:
                    continue
        return texts

    @staticmethod
    def _api_url(country: str) -> str:
        prefix = "" if country == "cn" else f"{country}."
        return f"https://{prefix}api.io.mi.com/app"

    def _encrypted_call(self, url: str, params: dict[str, str]) -> Any:
        headers = {
            "Accept-Encoding": "identity",
            "User-Agent": self._agent,
            "Content-Type": "application/x-www-form-urlencoded",
            "x-xiaomi-protocal-flag-cli": "PROTOCAL-HTTP2",
            "MIOT-ENCRYPT-ALGORITHM": "ENCRYPT-RC4",
        }
        cookies = {
            "userId": str(self._user_id),
            "yetAnotherServiceToken": str(self._service_token),
            "serviceToken": str(self._service_token),
            "locale": "en_GB",
            "timezone": "GMT+02:00",
            "is_daylight": "1",
            "dst_offset": "3600000",
            "channel": "MI_APP_STORE",
        }
        millis = round(time.time() * 1000)
        nonce = self._gen_nonce(millis)
        signed_nonce = self._signed_nonce(nonce)
        fields = self._gen_enc_params(url, "POST", signed_nonce, nonce, dict(params))
        response = self._session.post(
            url, headers=headers, cookies=cookies, params=fields, timeout=10
        )
        if response.status_code != _HTTP_OK:
            return None
        decoded = self._decrypt_rc4(self._signed_nonce(fields["_nonce"]), response.text)
        return json.loads(decoded)

    def _signed_nonce(self, nonce: str) -> str:
        if self._ssecurity is None:
            msg = "ssecurity not set; login required before signing requests"
            raise XiaomiCloudError(msg)
        h = hashlib.sha256(base64.b64decode(self._ssecurity) + base64.b64decode(nonce))
        return base64.b64encode(h.digest()).decode("utf-8")

    @staticmethod
    def _gen_nonce(millis: int) -> str:
        nonce_bytes = os.urandom(8) + (int(millis / 60000)).to_bytes(4, "big")
        return base64.b64encode(nonce_bytes).decode()

    @staticmethod
    def _gen_agent() -> str:
        agent_id = "".join(chr(random.randint(65, 69)) for _ in range(13))  # noqa: S311
        random_text = "".join(chr(random.randint(97, 122)) for _ in range(18))  # noqa: S311
        return f"{random_text}-{agent_id} APP/com.xiaomi.mihome APPV/10.5.201"

    @staticmethod
    def _gen_device_id() -> str:
        return "".join(chr(random.randint(97, 122)) for _ in range(6))  # noqa: S311

    def _gen_enc_params(
        self,
        url: str,
        method: str,
        signed_nonce: str,
        nonce: str,
        params: dict[str, str],
    ) -> dict[str, str]:
        if self._ssecurity is None:
            msg = "ssecurity not set; login required before encrypting requests"
            raise XiaomiCloudError(msg)
        params["rc4_hash__"] = self._enc_signature(url, method, signed_nonce, params)
        for k, v in params.items():
            params[k] = self._encrypt_rc4(signed_nonce, v)
        params.update(
            {
                "signature": self._enc_signature(url, method, signed_nonce, params),
                "ssecurity": self._ssecurity,
                "_nonce": nonce,
            }
        )
        return params

    @staticmethod
    def _enc_signature(
        url: str, method: str, signed_nonce: str, params: dict[str, str]
    ) -> str:
        parts = [method.upper(), url.split("com")[1].replace("/app/", "/")]
        for k, v in params.items():
            parts.append(f"{k}={v}")
        parts.append(signed_nonce)
        return base64.b64encode(
            hashlib.sha1("&".join(parts).encode("utf-8")).digest()  # noqa: S324
        ).decode()

    @staticmethod
    def _encrypt_rc4(password: str, payload: str) -> str:
        r = ARC4.new(base64.b64decode(password))
        r.encrypt(bytes(1024))
        return base64.b64encode(r.encrypt(payload.encode())).decode()

    @staticmethod
    def _decrypt_rc4(password: str, payload: str) -> bytes:
        r = ARC4.new(base64.b64decode(password))
        r.encrypt(bytes(1024))
        return r.encrypt(base64.b64decode(payload))

    @staticmethod
    def _to_json(text: str) -> Any:
        return json.loads(text.replace("&&&START&&&", ""))


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
        when a code we have not seen before appears.
        """
        if not self._logged_in or not self._device or not code:
            return None
        if code not in self._fault_texts:
            try:
                texts = await self._run(
                    self._connector.get_device_fault_texts,
                    self._device.country,
                    self._device.device_id,
                )
            except (requests.RequestException, XiaomiCloudError) as exc:
                LOGGER.debug("Failed to fetch fault texts: %s", exc)
                return None
            self._fault_texts.update(texts)
        return self._fault_texts.get(int(code))

    async def _run(self, func: Any, *args: Any) -> Any:
        return await self._hass.async_add_executor_job(partial(func, *args))
