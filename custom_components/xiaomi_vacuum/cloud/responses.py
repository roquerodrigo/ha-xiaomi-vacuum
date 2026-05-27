"""Typed shapes for the Xiaomi cloud API responses parsed by the connector."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class QrInit(TypedDict):
    """`loginUrl` response: QR image URL, long-poll URL, and its timeout."""

    qr: str
    lp: str
    timeout: NotRequired[int]


class QrPoll(TypedDict):
    """Long-poll login response returned once the user scans the QR code."""

    ssecurity: NotRequired[str]
    userId: NotRequired[str | int]
    location: NotRequired[str]


class HomeEntry(TypedDict):
    """A single home from the `gethome` response."""

    id: int
    uid: int


class HomesResult(TypedDict):
    """`gethome` result: owned and shared home lists."""

    homelist: NotRequired[list[HomeEntry]]
    share_home_list: NotRequired[list[HomeEntry]]


class DeviceEntry(TypedDict):
    """A single device from the `home_device_list` response."""

    did: str
    name: str
    model: str
    token: str
    localip: NotRequired[str | None]
    local_ip: NotRequired[str | None]
    mac: NotRequired[str | None]


class DevicesResult(TypedDict):
    """`home_device_list` result."""

    device_info: NotRequired[list[DeviceEntry]]


class MapUrlResult(TypedDict):
    """`get_interim_file_url` result: a temporary download URL."""

    url: NotRequired[str]


class FaultBody(TypedDict):
    """Device-message body carrying the active fault code(s)."""

    value: NotRequired[list[int]]
    extra: NotRequired[list[int]]


class FaultParams(TypedDict):
    """Device-message `params` wrapper."""

    body: NotRequired[FaultBody]


class FaultMessage(TypedDict):
    """A single device-push message: localized fault text plus its code."""

    title: NotRequired[str]
    params: NotRequired[FaultParams]


class FaultResult(TypedDict):
    """`message/v2/list` result: the device message feed."""

    messages: NotRequired[list[FaultMessage]]
