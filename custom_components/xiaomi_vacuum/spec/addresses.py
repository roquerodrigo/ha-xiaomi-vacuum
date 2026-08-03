"""MIoT address shapes shared by the property and action mappings."""

from __future__ import annotations

from typing import TypedDict


class MiotPropertyAddress(TypedDict):
    """``{siid, piid}`` address of a MIoT property."""

    siid: int
    piid: int


class MiotActionAddress(TypedDict):
    """``{siid, aiid}`` address of a MIoT action."""

    siid: int
    aiid: int


class MiotActionInputAddress(MiotActionAddress):
    """A :class:`MiotActionAddress` that also takes a property as its input."""

    in_piid: int
