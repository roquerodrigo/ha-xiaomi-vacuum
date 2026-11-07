"""
Room list decoded from a Dreame cloud map (X20+).

Dreame-built models publish no room property: the rooms live in the metadata
trailer of the map blob kept in the Xiaomi cloud. The blob is a JSON envelope
``{"mapstr": [{"id", "map", ...}], "curr_id"}`` whose ``map`` field is a
url-safe base64 zlib frame: a 27-byte header, ``width * height`` pixel bytes,
then a JSON trailer whose ``seg_inf`` maps each segment id to its metadata,
with the room name base64-encoded.
"""

from __future__ import annotations

import base64
import binascii
import contextlib
import json
import zlib
from typing import TYPE_CHECKING

from homeassistant.components.vacuum import Segment

from ..const import LOGGER  # noqa: TID252

if TYPE_CHECKING:
    from ..data import JsonValue  # noqa: TID252

_HEADER_SIZE = 27
_WIDTH_OFFSET = 19
_HEIGHT_OFFSET = 21


def dreame_map_object_name(raw_field: str | None) -> str | None:
    """Return the cloud object name from the map-object property's JSON."""
    if not raw_field:
        return None
    with contextlib.suppress(ValueError, TypeError):
        payload: JsonValue = json.loads(raw_field)
        if isinstance(payload, dict) and (name := payload.get("object_name")):
            return str(name)
    return None


def parse_dreame_rooms(raw: bytes) -> list[Segment]:
    """Decode the named rooms of a Dreame map blob, ordered by segment id."""
    try:
        trailer = _map_trailer(raw)
    except (TypeError, ValueError, zlib.error) as exception:
        LOGGER.warning("Failed to decode the Dreame map: %s", exception)
        return []
    rooms = trailer.get("seg_inf") if isinstance(trailer, dict) else None
    if not isinstance(rooms, dict):
        LOGGER.debug("Dreame map carries no segment metadata")
        return []
    segments: list[Segment] = []
    for room_id, info in sorted(rooms.items(), key=lambda item: _sort_key(item[0])):
        name = _room_name(info)
        # Unnamed segments are usually doorways the lidar mapped as rooms.
        if name:
            segments.append(Segment(id=str(room_id), name=name))
    return segments


def _map_trailer(raw: bytes) -> JsonValue:
    """Unwrap the envelope and frame down to the JSON metadata trailer."""
    text = raw.decode("ascii").strip()
    if text.startswith("{"):
        envelope: JsonValue = json.loads(text)
        text = _current_map(envelope)
    # Url-safe base64; a ",<key>" suffix marks an AES-encrypted map.
    encoded, _, key = text.replace("_", "/").replace("-", "+").partition(",")
    if key:
        msg = "encrypted maps are not supported yet"
        raise ValueError(msg)
    try:
        blob = base64.b64decode(encoded + "=" * (-len(encoded) % 4))
    except binascii.Error as exception:
        msg = f"invalid base64: {exception}"
        raise ValueError(msg) from exception
    frame = zlib.decompress(blob)
    if len(frame) < _HEADER_SIZE:
        msg = "frame shorter than its header"
        raise ValueError(msg)
    width = int.from_bytes(frame[_WIDTH_OFFSET : _WIDTH_OFFSET + 2], "little")
    height = int.from_bytes(frame[_HEIGHT_OFFSET : _HEIGHT_OFFSET + 2], "little")
    trailer = frame[_HEADER_SIZE + width * height :]
    if not trailer:
        return None
    metadata: JsonValue = json.loads(trailer.decode("utf-8"))
    return metadata


def _current_map(envelope: JsonValue) -> str:
    """Pick the active map's encoded frame out of a saved-map envelope."""
    entries = envelope.get("mapstr") if isinstance(envelope, dict) else None
    if not isinstance(envelope, dict) or not isinstance(entries, list):
        msg = "unexpected map envelope"
        raise TypeError(msg)
    maps = [m for m in entries if isinstance(m, dict)]
    current = next((m for m in maps if m.get("id") == envelope.get("curr_id")), None)
    if current is None and maps:
        current = maps[0]
    frame = current.get("map") if current else None
    if not isinstance(frame, str):
        msg = "map envelope holds no map"
        raise TypeError(msg)
    return frame


def _room_name(info: JsonValue) -> str:
    """Decode a segment's base64 name, falling back to the raw value."""
    name = info.get("name") if isinstance(info, dict) else None
    if not isinstance(name, str) or not name:
        return ""
    try:
        return base64.b64decode(name, validate=True).decode("utf-8").strip()
    except binascii.Error, UnicodeDecodeError:
        return name.strip()


def _sort_key(room_id: str) -> tuple[int, str]:
    """Order numeric segment ids numerically, anything else after them."""
    return (int(room_id), "") if room_id.isdigit() else (1 << 30, room_id)
