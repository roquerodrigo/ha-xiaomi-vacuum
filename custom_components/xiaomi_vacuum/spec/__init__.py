"""
Per-model MIoT spec for the supported Xiaomi vacuums.

Each :class:`ModelSpec` bundles everything that differs between the supported
models (currently the X20 Max ``d109gl``, the S20+ ``b108gl``, the S40 Pro
``ov71gl`` and the Dreame-built X20+ ``c102gl``): the
SIID/PIID property mapping, the SIID/AIID action mapping, the status-code
table, the enumerations exposed as selects, the ``send_command`` whitelist,
and a few derived capabilities (dust arrest, sweep route, obstacle avoidance)
and mapped properties that decide whether some entities are created at all.

The models are siblings but their published miot-spec instances diverge
enough that a single shared mapping is wrong. Adding a model means adding one
module here and registering it in :mod:`.registry` — see ``ADDING_A_MODEL.md``.
"""

from __future__ import annotations

from .addresses import (
    MiotActionAddress,
    MiotActionInputAddress,
    MiotPropertyAddress,
    MiotPropertyBinding,
    MiotSegmentCleanAddress,
)
from .b108gl import B108GL
from .c102gl import C102GL
from .capability import Capability
from .cleaning_job_signal import CleaningJobSignal
from .d109gl import D109GL
from .entity_key import EntityKey
from .fault_reading import FaultIdsReading, FaultReading, PlainFaultReading
from .map_format import DreameMapFormat, MapFormat, XiaomiMapFormat
from .model_actions import ModelActions, _require_action
from .model_spec import (
    MAPPING_FIELDS,
    ModelSpec,
)
from .ov71gl import OV71GL
from .property import Property
from .registry import DEFAULT_MODEL, MODELS, SUPPORTED_MODELS, get_spec
from .room_cleaning import (
    ConfigThenCustomSweep,
    DirectRoomSweep,
    DreameSegmentClean,
    RoomCleaning,
    RoomCleaningError,
)
from .status_catalog import CANONICAL_STATUSES, STATUS_MEANINGS
from .status_meaning import StatusMeaning
from .status_slug import StatusSlug

__all__ = [
    "B108GL",
    "C102GL",
    "CANONICAL_STATUSES",
    "D109GL",
    "DEFAULT_MODEL",
    "MAPPING_FIELDS",
    "MODELS",
    "OV71GL",
    "STATUS_MEANINGS",
    "SUPPORTED_MODELS",
    "Capability",
    "CleaningJobSignal",
    "ConfigThenCustomSweep",
    "DirectRoomSweep",
    "DreameMapFormat",
    "DreameSegmentClean",
    "EntityKey",
    "FaultIdsReading",
    "FaultReading",
    "MapFormat",
    "MiotActionAddress",
    "MiotActionInputAddress",
    "MiotPropertyAddress",
    "MiotPropertyBinding",
    "MiotSegmentCleanAddress",
    "ModelActions",
    "ModelSpec",
    "PlainFaultReading",
    "Property",
    "RoomCleaning",
    "RoomCleaningError",
    "StatusMeaning",
    "StatusSlug",
    "XiaomiMapFormat",
    "_require_action",
    "get_spec",
]
