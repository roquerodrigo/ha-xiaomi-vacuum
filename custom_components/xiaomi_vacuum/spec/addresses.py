"""MIoT address shapes shared by the property and action mappings."""

from __future__ import annotations

from typing import TypedDict


class MiotPropertyAddress(TypedDict):
    """``{siid, piid}`` address of a MIoT property."""

    siid: int
    piid: int


class MiotPropertyBinding(MiotPropertyAddress, total=False):
    """
    How one :class:`Property` sits on the device: its address and encoding.

    ``mask`` makes the property own only those bits of a packed device value:
    reads expose the bits shifted down, writes keep every other bit as the
    device reports it (the X20+ cleaning mode in the low two bits of 4.23).
    ``boolean`` marks a property published as a real bool, written back as one
    instead of a ``0``/``1`` integer. ``polled`` set to False keeps a property
    out of the periodic poll, read only on demand.
    """

    mask: int
    boolean: bool
    polled: bool


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
