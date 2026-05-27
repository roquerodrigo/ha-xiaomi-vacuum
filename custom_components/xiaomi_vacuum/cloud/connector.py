"""Sync Xiaomi cloud connector — QR Code login + signed MIoT calls."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import random
import time
from http import HTTPStatus
from typing import TYPE_CHECKING, cast

import requests
from Crypto.Cipher import ARC4

from ..const import LOGGER  # noqa: TID252
from .device_info import XiaomiDeviceInfo
from .errors import XiaomiCloudError

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ..data import JsonObject, JsonValue  # noqa: TID252
    from .responses import (
        DevicesResult,
        FaultResult,
        HomeEntry,
        HomesResult,
        MapUrlResult,
        QrInit,
        QrPoll,
    )

_HTTP_OK = int(HTTPStatus.OK)
_QR_DEFAULT_LOCALE = "en_US"


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
        body = cast("QrInit", self._to_json(response.text))
        qr_bytes = self._session.get(body["qr"], timeout=10).content
        return qr_bytes, body["lp"], body.get("timeout", 60)

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
        body = cast("QrPoll", self._to_json(response.text))
        ssecurity = body.get("ssecurity")
        if ssecurity is None:
            LOGGER.debug("QR long-poll returned without ssecurity: %s", body)
            return False
        self._ssecurity = ssecurity
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
            yield from self._iter_home_devices(
                country, int(home["id"]), int(home["uid"])
            )

    def _iter_homes(self, country: str) -> Iterator[HomeEntry]:
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
        result = cast("HomesResult", response["result"] or {})
        for homes in (result.get("homelist"), result.get("share_home_list")):
            yield from homes or []

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
        for device in cast("DevicesResult", result).get("device_info") or []:
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
            if not response:
                continue
            result = cast("MapUrlResult", response.get("result") or {})
            if url_value := result.get("url"):
                return url_value
        return None

    def get_map_bytes(self, map_url: str) -> bytes | None:
        """Download the raw binary map from the temporary URL."""
        response = self._session.get(map_url, timeout=10)
        if response.status_code != _HTTP_OK:
            return None
        return cast("bytes", response.content)

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
        for message in cast("FaultResult", result).get("messages") or []:
            params_obj = message.get("params")
            body = params_obj.get("body") if params_obj else None
            value = (body.get("value") or body.get("extra")) if body else None
            title = message.get("title")
            if title and value:
                try:
                    texts.setdefault(int(value[0]), title)
                except ValueError, TypeError:
                    continue
        return texts

    @staticmethod
    def _api_url(country: str) -> str:
        prefix = "" if country == "cn" else f"{country}."
        return f"https://{prefix}api.io.mi.com/app"

    def _encrypted_call(self, url: str, params: dict[str, str]) -> JsonObject | None:
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
        return cast("JsonObject", json.loads(decoded))

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
    def _to_json(text: str) -> JsonValue:
        return cast("JsonValue", json.loads(text.replace("&&&START&&&", "")))
