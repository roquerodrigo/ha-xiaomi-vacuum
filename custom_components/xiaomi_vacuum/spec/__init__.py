"""
Per-model MIoT spec for the supported Xiaomi vacuums.

Each :class:`ModelSpec` bundles everything that differs between the supported
models (currently the X20 Max ``d109gl`` and the S20+ ``b108gl``): the
SIID/PIID property mapping, the SIID/AIID action mapping, the status-code
table, the enumerations exposed as selects, the ``send_command`` whitelist,
and a few derived capabilities (dust arrest, sweep route, obstacle avoidance)
that decide whether some entities are created at all.

The two models are siblings but their published miot-spec instances diverge
enough that a single shared mapping is wrong. Adding a model means adding one
module here and registering it in :mod:`.registry` — see ``ADDING_A_MODEL.md``.
"""

from __future__ import annotations

from .addresses import (
    MiotActionAddress,
    MiotActionInputAddress,
    MiotPropertyAddress,
)
from .b108gl import B108GL
from .capability import Capability
from .d109gl import D109GL
from .entity_key import EntityKey
from .model_actions import ModelActions, _require_action
from .model_spec import (
    MAPPING_FIELDS,
    FaultKind,
    ModelSpec,
    RoomCleanStrategy,
    StatusDef,
)
from .property import Property
from .registry import DEFAULT_MODEL, MODELS, SUPPORTED_MODELS, get_spec

__all__ = [
    "B108GL",
    "D109GL",
    "DEFAULT_MODEL",
    "MAPPING_FIELDS",
    "MODELS",
    "SUPPORTED_MODELS",
    "Capability",
    "EntityKey",
    "FaultKind",
    "MiotActionAddress",
    "MiotActionInputAddress",
    "MiotPropertyAddress",
    "ModelActions",
    "ModelSpec",
    "Property",
    "RoomCleanStrategy",
    "StatusDef",
    "_require_action",
    "get_spec",
]
