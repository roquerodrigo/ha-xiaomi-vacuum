"""The ways a model encodes its cloud map blob."""

from __future__ import annotations

from .dreame_map_format import DreameMapFormat
from .map_format import MapFormat
from .xiaomi_map_format import XiaomiMapFormat

__all__ = ["DreameMapFormat", "MapFormat", "XiaomiMapFormat"]
