"""Rectangular cleaning zone in the vacuum's map coordinates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ..data import JsonObject  # noqa: TID252

_CORNER_COUNT = 4


@dataclass(frozen=True)
class CleaningZone:
    """Axis-aligned rectangle in map millimetres, corners normalised on creation."""

    left: int
    bottom: int
    right: int
    top: int

    @classmethod
    def from_corners(cls, corners: Sequence[int]) -> CleaningZone:
        """Build a zone from two opposite corners given as ``[x1, y1, x2, y2]``."""
        if len(corners) != _CORNER_COUNT:
            msg = f"Failed to build zone: expected 4 coordinates, got {len(corners)}"
            raise ValueError(msg)
        x1, y1, x2, y2 = corners
        return cls(
            left=min(x1, x2),
            bottom=min(y1, y2),
            right=max(x1, x2),
            top=max(y1, y2),
        )

    @property
    def is_empty(self) -> bool:
        """Whether the rectangle has no area to clean."""
        return self.left == self.right or self.bottom == self.top

    def to_block(self) -> JsonObject:
        """Return the ``start-zone-sweep`` block the Mi Home plugin sends."""
        return {
            "blocks_region": [
                self.left,
                self.top,
                self.left,
                self.bottom,
                self.right,
                self.bottom,
                self.right,
                self.top,
            ],
            "blocks_attr": 0,
        }
