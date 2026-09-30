from __future__ import annotations

import pytest

from custom_components.xiaomi_vacuum.api import CleaningZone


def test_from_corners_normalises_opposite_corners():
    zone = CleaningZone.from_corners([890, 750, 260, 250])
    assert zone == CleaningZone(left=260, bottom=250, right=890, top=750)


def test_from_corners_rejects_wrong_length():
    with pytest.raises(ValueError, match="expected 4 coordinates"):
        CleaningZone.from_corners([1, 2, 3])


@pytest.mark.parametrize(
    ("corners", "expected"),
    [([0, 0, 0, 10], True), ([0, 0, 10, 0], True), ([0, 0, 10, 10], False)],
)
def test_is_empty(corners, expected):
    assert CleaningZone.from_corners(corners).is_empty is expected


def test_to_block_matches_mi_home_plugin_polygon():
    zone = CleaningZone.from_corners([260, 250, 890, 750])
    assert zone.to_block() == {
        "blocks_region": [260, 750, 260, 250, 890, 250, 890, 750],
        "blocks_attr": 0,
    }
