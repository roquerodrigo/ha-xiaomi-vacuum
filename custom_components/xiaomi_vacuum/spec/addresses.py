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


class MiotSegmentCleanAddress(MiotActionAddress):
    """
    A Dreame ``start-clean`` action: work mode plus clean-extend data inputs.

    Room cleaning sends the segment work mode on ``mode_piid`` and the JSON
    room selection on ``data_piid`` in one call.
    """

    mode_piid: int
    data_piid: int
