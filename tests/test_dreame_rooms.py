"""Decoding the room list out of a Dreame cloud map (X20+)."""

from __future__ import annotations

import pytest

from custom_components.xiaomi_vacuum.vacuum.dreame_rooms import (
    dreame_map_object_name,
    parse_dreame_rooms,
)


def _rooms(raw: bytes) -> list[tuple[str, str]]:
    return [(s.id, s.name) for s in parse_dreame_rooms(raw)]


def test_rooms_from_the_current_map_of_the_envelope(dreame_map, dreame_name):
    raw = dreame_map(
        {"10": {"name": dreame_name("Kitchen")}, "2": {"name": dreame_name("Hall")}}
    )
    assert _rooms(raw) == [("2", "Hall"), ("10", "Kitchen")]


def test_envelope_without_a_matching_current_id_uses_the_first_map(
    dreame_map, dreame_name
):
    import json

    encoded = dreame_map({"1": {"name": dreame_name("Hall")}}, envelope=False)
    raw = json.dumps({"mapstr": [{"id": 3, "map": encoded.decode()}]}).encode()
    assert _rooms(raw) == [("1", "Hall")]


def test_bare_frame_without_envelope(dreame_map, dreame_name):
    raw = dreame_map({"1": {"name": dreame_name("Hall")}}, envelope=False)
    assert _rooms(raw) == [("1", "Hall")]


def test_plain_text_names_and_odd_ids(dreame_map):
    raw = dreame_map({"x": {"name": "Not base64!"}, "3": {"name": "  "}})
    assert _rooms(raw) == [("x", "Not base64!")]


def test_name_that_is_base64_but_not_utf8_is_kept_raw(dreame_map):
    assert _rooms(dreame_map({"1": {"name": "//79"}})) == [("1", "//79")]


@pytest.mark.parametrize(
    "rooms",
    [None, {}, {"1": "not-a-dict"}],
    ids=["no-trailer", "no-rooms", "bad-room"],
)
def test_maps_without_named_rooms(dreame_map, rooms):
    assert _rooms(dreame_map(rooms)) == []


def test_trailer_without_seg_inf(dreame_map):
    import base64
    import json
    import zlib

    frame = bytes(27) + json.dumps({"walls_info": {}}).encode()
    raw = base64.b64encode(zlib.compress(frame))
    assert parse_dreame_rooms(raw) == []
    assert json.loads(dreame_map(None))["curr_id"] == 7


def test_encrypted_map_is_skipped(dreame_map, dreame_name, caplog):
    raw = dreame_map({"1": {"name": dreame_name("Hall")}}, key="secret")
    assert parse_dreame_rooms(raw) == []
    assert "encrypted" in caplog.text


@pytest.mark.parametrize(
    "raw",
    [
        b"garbage!",
        b"@@@@",
        b"AAAA",
        b'{"mapstr": "nope"}',
        b'{"mapstr": [{"id": 0}]}',
        b'{"mapstr": []}',
        b"[1, 2]",
    ],
    ids=[
        "not-base64",
        "bad-padding",
        "not-zlib",
        "bad-mapstr",
        "no-map",
        "empty",
        "array",
    ],
)
def test_undecodable_maps(raw):
    assert parse_dreame_rooms(raw) == []


def test_short_frame():
    import base64
    import zlib

    assert parse_dreame_rooms(base64.b64encode(zlib.compress(b"tiny"))) == []


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('{"object_name":"1/2/map.bin","md5":"x"}', "1/2/map.bin"),
        ('{"md5":"x"}', None),
        ("not json", None),
        ("[1]", None),
        ("", None),
        (None, None),
    ],
)
def test_map_object_name(raw, expected):
    assert dreame_map_object_name(raw) == expected
