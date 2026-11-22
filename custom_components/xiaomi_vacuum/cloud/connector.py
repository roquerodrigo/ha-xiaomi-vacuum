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
from cryptography.hazmat.decrepit.ciphers.algorithms import ARC4
from cryptography.hazmat.primitives.ciphers import Cipher

from ..const import LOGGER  # noqa: TID252
from .device_info import XiaomiDeviceInfo
from .errors import XiaomiCloudAuthError, XiaomiCloudConnectionError, XiaomiCloudError
from .redaction import response_key_names

if TYPE_CHECKING:
    from collections.abc import Iterator

    from cryptography.hazmat.primitives.ciphers import CipherContext

    from ..data import JsonObject, JsonValue  # noqa: TID252
    from ..spec.addresses import MiotEventAddress  # noqa: TID252
    from .responses import (
        DevicesResult,
        HomeEntry,
        HomesResult,
        MapUrlResult,
        QrInit,
        QrPoll,
    )

_HTTP_OK = int(HTTPStatus.OK)
# Xiaomi answers an expired ``serviceToken`` with 426 and a plain-text
# ``{"code":0,"message":"SERVICETOKEN_EXPIRED"}`` body — not 401/403.
_HTTP_AUTH_STATUSES = frozenset(
    {
        int(HTTPStatus.UNAUTHORIZED),
        int(HTTPStatus.FORBIDDEN),
        int(HTTPStatus.UPGRADE_REQUIRED),
    }
)
_QR_DEFAULT_LOCALE = "en_US"
_SERVICE_LOGIN_URL = "https://account.xiaomi.com/pass/serviceLogin"


class _XiaomiCloudConnector:
    """Sync client for the Xiaomi cloud — QR login + signed MIoT calls."""

    def __init__(self) -> None:
        """Initialize a fresh session with the standard SDK cookies."""
        self._agent = self._gen_agent()
        self._session = requests.session()
        for domain in ("mi.com", "xiaomi.com"):
            self._session.cookies.set("sdkVersion", "accountsdk-18.8.15", domain=domain)
        self._set_device_id(self._gen_device_id())
        self._ssecurity: str | None = None
        self._user_id: str | None = None
        self._service_token: str | None = None
        self._pass_token: str | None = None

    def _set_device_id(self, device_id: str) -> None:
        self._device_id = device_id
        for domain in ("mi.com", "xiaomi.com"):
            self._session.cookies.set("deviceId", device_id, domain=domain)

    @property
    def ssecurity(self) -> str | None:
        """The session's signing secret, or None before login."""
        return self._ssecurity

    @property
    def user_id(self) -> str | None:
        """The logged-in Xiaomi account id, or None before login."""
        return self._user_id

    @property
    def service_token(self) -> str | None:
        """The session's service token, or None before login."""
        return self._service_token

    @property
    def pass_token(self) -> str | None:
        """The long-lived login that can renew the session, if known."""
        return self._pass_token

    @property
    def device_id(self) -> str:
        """The client id this login was issued to."""
        return self._device_id

    def restore_session(
        self,
        ssecurity: str,
        user_id: str,
        service_token: str,
        pass_token: str | None = None,
        device_id: str | None = None,
    ) -> None:
        """Adopt previously issued session tokens instead of a fresh QR login."""
        self._ssecurity = ssecurity
        self._user_id = user_id
        self._service_token = service_token
        self._pass_token = pass_token
        if device_id:
            self._set_device_id(device_id)

    def refresh_session(self) -> bool:
        """
        Trade the long-lived ``passToken`` for a fresh session, without a QR scan.

        The ``serviceToken`` lives for weeks; the ``passToken`` issued by the
        same login outlives it and lets ``serviceLogin`` hand out a new
        session directly. Returns False when Xiaomi no longer accepts the
        ``passToken`` (it answers with a login challenge instead) — only then
        is a new QR scan needed.
        """
        if not self._pass_token or not self._user_id:
            return False
        response = self._session.get(
            _SERVICE_LOGIN_URL,
            params={"sid": "xiaomiio", "_json": "true"},
            cookies={"userId": self._user_id, "passToken": self._pass_token},
            timeout=10,
        )
        if response.status_code != _HTTP_OK:
            msg = f"Session refresh failed with HTTP {response.status_code}"
            raise XiaomiCloudConnectionError(msg)
        body = self._to_json(response.text)
        if not isinstance(body, dict):
            return False
        ssecurity = body.get("ssecurity")
        location = body.get("location")
        if not isinstance(ssecurity, str) or not isinstance(location, str):
            return False
        if not ssecurity or not location:
            LOGGER.debug("Session refresh declined; keys: %s", response_key_names(body))
            return False
        if not self._fetch_service_token(location):
            return False
        self._ssecurity = ssecurity
        pass_token = body.get("passToken")
        if isinstance(pass_token, str) and pass_token:
            self._pass_token = pass_token
        return True

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
        if response.status_code != _HTTP_OK:
            msg = f"QR login start failed with HTTP {response.status_code}"
            raise XiaomiCloudConnectionError(msg)
        raw_body = self._to_json(response.text)
        if not isinstance(raw_body, dict):
            msg = "QR login start returned an unexpected payload"
            raise XiaomiCloudError(msg)
        body = cast("QrInit", raw_body)
        qr_url = body.get("qr")
        long_polling_url = body.get("lp")
        if not qr_url or not long_polling_url:
            msg = "QR login start returned an unexpected payload"
            raise XiaomiCloudError(msg)
        qr_bytes = self._session.get(qr_url, timeout=10).content
        return qr_bytes, long_polling_url, body.get("timeout", 60)

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
            LOGGER.debug("QR long-poll status %s", response.status_code)
            return False
        body = cast("QrPoll", self._to_json(response.text))
        ssecurity = body.get("ssecurity")
        if ssecurity is None:
            LOGGER.debug(
                "QR long-poll returned without ssecurity; keys: %s",
                response_key_names(body),
            )
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
        for device in self.iter_devices(country):
            if device.token.casefold() == token.casefold():
                return device
        return None

    def iter_devices(self, country: str) -> Iterator[XiaomiDeviceInfo]:
        """Yield every device of every home (own and shared) in the country."""
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
        response = self._encrypted_call(url, params, raise_for_status=True)
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
        response = self._encrypted_call(url, params, raise_for_status=True)
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

    def call_action(
        self, country: str, did: str, siid: int, aiid: int, params: list[str] | None
    ) -> JsonObject | None:
        """
        Invoke a MIoT action through the cloud (reliable TCP) instead of local UDP.

        Local miio actions on Xiaomi vacuums frequently hit ``-9999 user ack
        timeout`` on flaky Wi-Fi; the Mi Home app sidesteps this by issuing
        actions over the cloud HTTP API. We replicate that path here so
        multi-step flows (e.g. the S20+ room-clean) succeed reliably. Payload
        shape matches what the app sends (captured): ``{"params": {did, siid,
        aiid, in}}``.
        """
        url = self._api_url(country) + "/miotspec/action"
        params_payload = {
            "did": str(did),
            "siid": siid,
            "aiid": aiid,
            "in": params or [],
        }
        request_params = {"data": json.dumps({"params": params_payload})}
        response = self._encrypted_call(url, request_params)
        if not response:
            return None
        return response

    def get_map_bytes(self, map_url: str) -> bytes | None:
        """Download the raw binary map from the temporary URL."""
        response = self._session.get(map_url, timeout=10)
        if response.status_code != _HTTP_OK:
            return None
        return cast("bytes", response.content)

    def _get_fault_messages(
        self, country: str, did: str, limit: int, *, strict: bool
    ) -> list[JsonValue]:
        """Read the shared message feed without changing notification status."""
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
        response = self._encrypted_call(url, params, raise_for_status=strict)
        result = response.get("result") if isinstance(response, dict) else None
        messages = result.get("messages") if isinstance(result, dict) else None
        if isinstance(messages, list):
            return messages
        return []

    @staticmethod
    def _fault_code(value: JsonValue) -> int | None:
        if not isinstance(value, list) or not value:
            return None
        raw_code = value[0]
        if not isinstance(raw_code, (str, int, float)) or isinstance(raw_code, bool):
            return None
        try:
            code = int(raw_code)
        except ValueError, TypeError, OverflowError:
            return None
        if code <= 0 or (isinstance(raw_code, float) and raw_code != code):
            return None
        return code

    @staticmethod
    def _parse_fault_message(
        message: JsonValue, *, event_id: str | None
    ) -> dict[str, str | int] | None:
        """Extract the fault data of a message filed under ``event_id``, if given."""
        if not isinstance(message, dict):
            return None
        params = message.get("params")
        body = params.get("body") if isinstance(params, dict) else None
        if not isinstance(body, dict):
            return None
        if event_id is not None and body.get("event") != event_id:
            return None
        code = _XiaomiCloudConnector._fault_code(body.get("value") or body.get("extra"))
        if code is None:
            return None
        event: dict[str, str | int] = {"code": code}
        title = message.get("title")
        if isinstance(title, str) and title:
            event["text"] = title
        timestamp = message.get("ctime") or message.get("time")
        if (
            isinstance(timestamp, int)
            and not isinstance(timestamp, bool)
            and timestamp > 0
        ):
            event["timestamp"] = timestamp
        return event

    def get_device_fault_messages(
        self, country: str, did: str, fault_event: MiotEventAddress, limit: int = 50
    ) -> list[dict[str, str | int]]:
        """Return up to 50 recent ``fault_event`` messages without marking them read."""
        limit = min(50, max(1, limit))
        event_id = f"{fault_event['siid']}.{fault_event['eiid']}"
        messages = self._get_fault_messages(country, did, limit, strict=True)
        events: list[dict[str, str | int]] = []
        for message in messages:
            event = self._parse_fault_message(message, event_id=event_id)
            if event is not None:
                events.append(event)
                if len(events) == limit:
                    break
        return events

    def get_device_fault_texts(
        self, country: str, did: str, limit: int = 50
    ) -> dict[int, str]:
        """Map fault codes to localized text, retaining legacy feed compatibility."""
        texts: dict[int, str] = {}
        for message in self._get_fault_messages(country, did, limit, strict=False):
            event = self._parse_fault_message(message, event_id=None)
            if event is not None and isinstance(title := event.get("text"), str):
                texts.setdefault(int(event["code"]), title)
        return texts

    @staticmethod
    def _api_url(country: str) -> str:
        prefix = "" if country == "cn" else f"{country}."
        return f"https://{prefix}api.io.mi.com/app"

    def _encrypted_call(
        self, url: str, params: dict[str, str], *, raise_for_status: bool = False
    ) -> JsonObject | None:
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
        if response.status_code in _HTTP_AUTH_STATUSES:
            msg = (
                "Xiaomi cloud rejected the session "
                f"(HTTP {response.status_code}{self._rejection_reason(response)})"
            )
            raise XiaomiCloudAuthError(msg)
        if response.status_code != _HTTP_OK:
            if raise_for_status:
                msg = f"Xiaomi cloud returned HTTP {response.status_code} for {url}"
                raise XiaomiCloudConnectionError(msg)
            return None
        decoded = self._decrypt_rc4(self._signed_nonce(fields["_nonce"]), response.text)
        return cast("JsonObject", json.loads(decoded))

    @staticmethod
    def _rejection_reason(response: requests.Response) -> str:
        try:
            body = json.loads(response.text)
        except ValueError:
            return ""
        message = body.get("message") if isinstance(body, dict) else None
        return f": {message}" if isinstance(message, str) and message else ""

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
        r = _rc4_stream(password)
        return base64.b64encode(r.update(payload.encode())).decode()

    @staticmethod
    def _decrypt_rc4(password: str, payload: str) -> bytes:
        r = _rc4_stream(password)
        return r.update(base64.b64decode(payload))

    @staticmethod
    def _to_json(text: str) -> JsonValue:
        return cast("JsonValue", json.loads(text.replace("&&&START&&&", "")))


def _rc4_stream(password: str) -> CipherContext:
    """RC4 keystream primed like the Mi Home app: the first 1024 bytes are discarded."""
    stream = Cipher(ARC4(base64.b64decode(password)), mode=None).encryptor()
    stream.update(bytes(1024))
    return stream
