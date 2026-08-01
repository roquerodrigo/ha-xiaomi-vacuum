"""
Per-model MIoT spec for the supported Xiaomi vacuums.

Each :class:`ModelSpec` bundles everything that differs between the supported
models (currently the X20 Max ``d109gl`` and the S20+ ``b108gl``): the
SIID/PIID property mapping, the SIID/AIID action mapping, the status-code
tables, the enumerations exposed as selects, the ``send_command`` whitelist,
and a few capability flags (dust arrest, mop-wash dock, sweep route, obstacle
avoidance) that decide whether some entities are created at all.

The two models are siblings but their published miot-spec instances diverge
enough (different PIIDs for status/fault, different services for continue/
return-home/identify, different status-code sets, S20+ lacks the auto-wash
dock and the sweep-route / obstacle-avoidance properties) that a single shared
mapping is wrong. Sources:

- d109gl v2: urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-d109gl:2
- b108gl v1: urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-b108gl:1
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, TypedDict, cast

from homeassistant.components.vacuum.const import VacuumActivity

# How the live fault is read. d109gl publishes a `Fault Ids` JSON list
# ({"fault":[codes]}); b108gl publishes a plain `fault` uint32 (0 == healthy).
FaultKind = Literal["ids", "simple"]

# How room cleaning is initiated.
# - "direct": a single `start-vacuum-room-sweep` action takes the room ids
#   as input (X20 Max).
# - "config_then_custom": the app first marks the target rooms via
#   `set-room-clean-configs` (setting their `on` flag), then fires
#   `start-custom-sweep` with no params (S20+). Captured from the Mi Home app.
RoomCleanStrategy = Literal["direct", "config_then_custom"]


class Property(StrEnum):
    """Symbolic name for a MIoT property exposed by the integration."""

    STATUS = "status"
    FAULT_IDS = "fault_ids"
    FAULT = "fault"
    SWEEP_MOP_TYPE = "sweep_mop_type"
    CLEANING_AREA = "cleaning_area"
    CLEANING_TIME = "cleaning_time"
    CLEAN_TIMES = "clean_times"
    FAN_SPEED = "fan_speed"
    MOP_WATER_LEVEL = "mop_water_level"
    ROOM_INFORMATION = "room_information"
    LAST_CLEAN_TIME = "last_clean_time"
    MAP_OBJ_NAME = "map_obj_name"
    SWEEP_ROUTE = "sweep_route"
    OBSTACLE_AVOIDANCE_STRATEGY = "obstacle_avoidance_strategy"
    BATTERY_LEVEL = "battery_level"
    CHARGING_STATE = "charging_state"
    MOP_LIFE = "mop_life"
    MAIN_BRUSH_LIFE = "main_brush_life"
    SIDE_BRUSH_LIFE = "side_brush_life"
    FILTER_LIFE = "filter_life"


class EntityKey(StrEnum):
    """Stable key identifying a concrete entity across all platforms."""

    VACUUM = "vacuum"
    BATTERY_SENSOR = "battery"
    STATUS_SENSOR = "status"
    ERROR_SENSOR = "error"
    ERROR_CODE_SENSOR = "error_code"
    MOP_LIFE_SENSOR = "mop_life"
    MAIN_BRUSH_LIFE_SENSOR = "main_brush_life"
    SIDE_BRUSH_LIFE_SENSOR = "side_brush_life"
    FILTER_LIFE_SENSOR = "filter_life"
    BATTERY_CHARGING_SENSOR = "battery_charging"
    MAP_IMAGE = "map"
    SWEEP_MOP_TYPE_SELECT = "sweep_mop_type"
    CLEAN_TIMES_SELECT = "clean_times"
    MOP_WATER_LEVEL_SELECT = "mop_water_level"
    SWEEP_ROUTE_SELECT = "sweep_route"
    OBSTACLE_AVOIDANCE_SELECT = "obstacle_avoidance_strategy"
    DUST_ARREST_BUTTON = "dust_arrest"


class Capability(StrEnum):
    """Model-level capability that gates entity creation on a platform."""

    DUST_ARREST = "dust_arrest"
    SWEEP_ROUTE = "sweep_route"
    OBSTACLE_AVOIDANCE = "obstacle_avoidance"
    MOP_WASH_DRY = "mop_wash_dry"


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


class StatusDef(TypedDict):
    """Per-status-code metadata: HA activity, slug, and idle flag."""

    activity: VacuumActivity
    slug: str
    is_idle: bool


#: Maps each optional :class:`Capability` to the :class:`EntityKey` it gates.
_CAPABILITY_ENTITIES: dict[Capability, EntityKey] = {
    Capability.DUST_ARREST: EntityKey.DUST_ARREST_BUTTON,
    Capability.SWEEP_ROUTE: EntityKey.SWEEP_ROUTE_SELECT,
    Capability.OBSTACLE_AVOIDANCE: EntityKey.OBSTACLE_AVOIDANCE_SELECT,
}

#: Entities every supported vacuum exposes regardless of capabilities.
_BASE_ENTITIES: frozenset[EntityKey] = frozenset(
    {
        EntityKey.VACUUM,
        EntityKey.BATTERY_SENSOR,
        EntityKey.STATUS_SENSOR,
        EntityKey.ERROR_SENSOR,
        EntityKey.ERROR_CODE_SENSOR,
        EntityKey.MOP_LIFE_SENSOR,
        EntityKey.MAIN_BRUSH_LIFE_SENSOR,
        EntityKey.SIDE_BRUSH_LIFE_SENSOR,
        EntityKey.FILTER_LIFE_SENSOR,
        EntityKey.BATTERY_CHARGING_SENSOR,
        EntityKey.SWEEP_MOP_TYPE_SELECT,
        EntityKey.CLEAN_TIMES_SELECT,
        EntityKey.MOP_WATER_LEVEL_SELECT,
    }
)


@dataclass(frozen=True)
class ModelActions:
    """MIoT action addresses (``{siid, aiid}`` and optional ``in_piid``)."""

    start_sweep: MiotActionAddress
    stop_sweeping: MiotActionAddress
    return_home: MiotActionAddress
    start_only_sweep: MiotActionAddress
    start_mop: MiotActionAddress
    start_sweep_mop: MiotActionAddress
    pause_sweeping: MiotActionAddress
    continue_sweep: MiotActionAddress
    identify: MiotActionAddress
    # Room cleaning. X20 Max uses a single direct action that takes room ids;
    # S20+ has no such action and instead configures rooms (below) then fires
    # start-custom-sweep.
    start_room_sweep: MiotActionInputAddress | None = None
    set_room_clean_configs: MiotActionAddress | None = None
    start_custom_sweep: MiotActionAddress | None = None
    # Dock-only actions; None when the model has no such hardware (S20+).
    start_dust_arrest: MiotActionAddress | None = None
    start_mop_wash: MiotActionAddress | None = None
    start_dry: MiotActionAddress | None = None
    stop_mop_wash: MiotActionAddress | None = None
    stop_dry: MiotActionAddress | None = None


@dataclass(frozen=True)
class ModelSpec:
    """Everything model-specific the integration needs at runtime."""

    model: str
    name: str
    property_mapping: dict[Property, MiotPropertyAddress]
    actions: ModelActions
    status: dict[int, StatusDef]
    fan_speeds: dict[str, int]
    sweep_mop_types: dict[str, int]
    clean_times: dict[str, int]
    mop_water_levels: dict[str, int]
    send_commands: dict[str, MiotActionAddress]
    fault_kind: FaultKind
    room_clean_strategy: RoomCleanStrategy

    @property
    def status_to_activity(self) -> dict[int, VacuumActivity]:
        """Status code → HA activity, derived from :attr:`status`."""
        return {code: s["activity"] for code, s in self.status.items()}

    @property
    def status_slugs(self) -> dict[int, str]:
        """Status code → translation slug, derived from :attr:`status`."""
        return {code: s["slug"] for code, s in self.status.items()}

    @property
    def idle_statuses(self) -> frozenset[int]:
        """Status codes that count as parked/idle (a fresh start is safe)."""
        return frozenset(code for code, s in self.status.items() if s["is_idle"])

    def status_code_for(self, activity: VacuumActivity) -> int:
        """
        First status code whose activity matches ``activity``.

        Used by optimistic UI patches so a command reports the same activity the
        device will confirm on the next poll, without the platform hard-coding
        per-model status codes (X20 Max and S20+ already diverge elsewhere).
        Order is insertion order of :attr:`status`, which lists the canonical
        representative (e.g. ``sweeping`` for CLEANING) first.
        """
        for code, definition in self.status.items():
            if definition["activity"] is activity:
                return code
        msg = f"No status code maps to activity {activity!r}"
        raise ValueError(msg)

    @property
    def capabilities(self) -> frozenset[Capability]:
        """The set of capabilities this model advertises, derived from its spec."""
        caps: set[Capability] = set()
        if self.actions.start_dust_arrest is not None:
            caps.add(Capability.DUST_ARREST)
        if Property.SWEEP_ROUTE in self.property_mapping:
            caps.add(Capability.SWEEP_ROUTE)
        if Property.OBSTACLE_AVOIDANCE_STRATEGY in self.property_mapping:
            caps.add(Capability.OBSTACLE_AVOIDANCE)
        if self.actions.start_mop_wash is not None:
            caps.add(Capability.MOP_WASH_DRY)
        return frozenset(caps)

    @property
    def entities(self) -> frozenset[EntityKey]:
        """Entities to create for this model: base set plus capability-gated ones."""
        keys = set(_BASE_ENTITIES)
        for cap in self.capabilities:
            if (key := _CAPABILITY_ENTITIES.get(cap)) is not None:
                keys.add(key)
        return frozenset(keys)

    @property
    def fan_speed_names(self) -> dict[int, str]:
        """Reverse of :attr:`fan_speeds` (value→slug)."""
        return {v: k for k, v in self.fan_speeds.items()}

    @property
    def sweep_mop_type_names(self) -> dict[int, str]:
        """Reverse of :attr:`sweep_mop_types` (value→slug)."""
        return {v: k for k, v in self.sweep_mop_types.items()}

    @property
    def clean_times_names(self) -> dict[int, str]:
        """Reverse of :attr:`clean_times` (value→slug)."""
        return {v: k for k, v in self.clean_times.items()}

    @property
    def mop_water_level_names(self) -> dict[int, str]:
        """Reverse of :attr:`mop_water_levels` (value→slug)."""
        return {v: k for k, v in self.mop_water_levels.items()}

    @property
    def has_dust_arrest(self) -> bool:
        """Whether the dock can empty the dust bin (X20 Max auto-dust dock)."""
        return Capability.DUST_ARREST in self.capabilities

    @property
    def has_sweep_route(self) -> bool:
        """Whether the model exposes the sweep-route property."""
        return Capability.SWEEP_ROUTE in self.capabilities

    @property
    def has_obstacle_avoidance(self) -> bool:
        """Whether the model exposes the obstacle-avoidance property."""
        return Capability.OBSTACLE_AVOIDANCE in self.capabilities

    @property
    def has_mop_wash_dry(self) -> bool:
        """Whether the dock can wash and dry the mop (X20 Max auto-wash dock)."""
        return Capability.MOP_WASH_DRY in self.capabilities


# --------------------------------------------------------------------------- #
# Shared enumerations (identical on both models)
# --------------------------------------------------------------------------- #

_FAN_SPEEDS: dict[str, int] = {
    "silent": 1,
    "basic": 2,
    "strong": 3,
    "full_speed": 4,
}

_SWEEP_MOP_TYPES: dict[str, int] = {
    "sweep": 1,
    "mop": 2,
    "sweep_mop": 3,
    "sweep_before_mopping": 4,
}

_CLEAN_TIMES: dict[str, int] = {
    "one_time": 1,
    "two_times": 2,
}

_CHARGING_STATE_SLUGS: dict[int, str] = {
    1: "charging",
    2: "not_charging",
    3: "not_chargeable",
}

# Mop water levels differ: S20+ exposes an explicit "off" (0); X20 Max does not.
_MOP_WATER_LEVELS_D109: dict[str, int] = {
    "level_1": 1,
    "level_2": 2,
    "level_3": 3,
}
_MOP_WATER_LEVELS_B108: dict[str, int] = {
    "off": 0,
    "level_1": 1,
    "level_2": 2,
    "level_3": 3,
}

_SWEEP_ROUTES: dict[str, int] = {
    "quick": 1,
    "daily": 2,
    "careful": 3,
}

_OBSTACLE_AVOIDANCES: dict[str, int] = {
    "less_collisions": 0,
    "high_coverage": 1,
}


def _cast_action(action: MiotActionAddress | None) -> MiotActionAddress:
    """Narrow an optional action to non-None for whitelists (d109gl dock actions)."""
    return cast("MiotActionAddress", action)


# --------------------------------------------------------------------------- #
# Xiaomi Robot Vacuum X20 Max — xiaomi.vacuum.d109gl (spec v2)
# --------------------------------------------------------------------------- #

_D109_PROPERTY_MAPPING: dict[Property, MiotPropertyAddress] = {
    Property.STATUS: {"siid": 2, "piid": 2},
    # Live fault state. The Device Fault property (piid 3) is deliberately NOT
    # read: it latches the last code and never resets. Fault Ids (piid 66) is
    # the live {"fault": [codes]} list ([0] = none).
    Property.FAULT_IDS: {"siid": 2, "piid": 66},
    Property.SWEEP_MOP_TYPE: {"siid": 2, "piid": 4},
    Property.CLEANING_AREA: {"siid": 2, "piid": 6},
    Property.CLEANING_TIME: {"siid": 2, "piid": 7},
    Property.CLEAN_TIMES: {"siid": 2, "piid": 8},
    Property.FAN_SPEED: {"siid": 2, "piid": 9},
    Property.MOP_WATER_LEVEL: {"siid": 2, "piid": 10},
    Property.ROOM_INFORMATION: {"siid": 2, "piid": 16},
    Property.LAST_CLEAN_TIME: {"siid": 2, "piid": 17},
    Property.MAP_OBJ_NAME: {"siid": 10, "piid": 1},
    Property.SWEEP_ROUTE: {"siid": 2, "piid": 74},
    Property.OBSTACLE_AVOIDANCE_STRATEGY: {"siid": 2, "piid": 75},
    Property.BATTERY_LEVEL: {"siid": 3, "piid": 1},
    Property.CHARGING_STATE: {"siid": 3, "piid": 2},
    Property.MOP_LIFE: {"siid": 9, "piid": 1},
    Property.MAIN_BRUSH_LIFE: {"siid": 12, "piid": 1},
    Property.SIDE_BRUSH_LIFE: {"siid": 13, "piid": 1},
    Property.FILTER_LIFE: {"siid": 14, "piid": 1},
}

_D109_ACTIONS = ModelActions(
    start_sweep={"siid": 2, "aiid": 1},
    stop_sweeping={"siid": 2, "aiid": 2},
    return_home={"siid": 2, "aiid": 3},
    start_only_sweep={"siid": 2, "aiid": 4},
    start_mop={"siid": 2, "aiid": 5},
    start_sweep_mop={"siid": 2, "aiid": 6},
    pause_sweeping={"siid": 2, "aiid": 7},
    # Resume a paused job (vs. start_sweep, which begins a fresh clean).
    continue_sweep={"siid": 2, "aiid": 8},
    start_room_sweep={"siid": 2, "aiid": 16, "in_piid": 15},
    identify={"siid": 6, "aiid": 1},
    start_dust_arrest={"siid": 2, "aiid": 18},
    start_mop_wash={"siid": 2, "aiid": 19},
    start_dry={"siid": 2, "aiid": 20},
    stop_mop_wash={"siid": 2, "aiid": 31},
    stop_dry={"siid": 2, "aiid": 32},
)

# The ERROR activity is NOT produced from status: an active fault drives it (see
# XiaomiVacuum.activity). Break/interrupt statuses (3 BreakCharging, 19 GoChargeBreak,
# 20 WashBreak) and the bare "Error" status (15) occur with no active fault during
# normal cycles, so they map to their nearest non-error activity instead.
# is_idle = parked at the dock and safe to start a fresh clean from (1 Idle,
# 2 Charging, 9 Charged).
_D109_STATUS: dict[int, StatusDef] = {
    1: {"activity": VacuumActivity.IDLE, "slug": "idle", "is_idle": True},
    2: {"activity": VacuumActivity.DOCKED, "slug": "charging", "is_idle": True},
    3: {"activity": VacuumActivity.DOCKED, "slug": "break_charging", "is_idle": False},
    4: {"activity": VacuumActivity.CLEANING, "slug": "sweeping", "is_idle": False},
    5: {"activity": VacuumActivity.PAUSED, "slug": "paused", "is_idle": False},
    6: {"activity": VacuumActivity.RETURNING, "slug": "go_charging", "is_idle": False},
    7: {"activity": VacuumActivity.RETURNING, "slug": "go_wash", "is_idle": False},
    8: {"activity": VacuumActivity.CLEANING, "slug": "remote", "is_idle": False},
    9: {"activity": VacuumActivity.DOCKED, "slug": "charged", "is_idle": True},
    10: {"activity": VacuumActivity.CLEANING, "slug": "building_map", "is_idle": False},
    11: {"activity": VacuumActivity.IDLE, "slug": "updating", "is_idle": False},
    12: {
        "activity": VacuumActivity.DOCKED,
        "slug": "multi_task_station_working",
        "is_idle": False,
    },
    13: {
        "activity": VacuumActivity.RETURNING,
        "slug": "multi_task_recharge",
        "is_idle": False,
    },
    14: {
        "activity": VacuumActivity.DOCKED,
        "slug": "station_working",
        "is_idle": False,
    },
    15: {"activity": VacuumActivity.IDLE, "slug": "error", "is_idle": False},
    16: {
        "activity": VacuumActivity.CLEANING,
        "slug": "sweeping_and_mopping",
        "is_idle": False,
    },
    17: {"activity": VacuumActivity.CLEANING, "slug": "mopping", "is_idle": False},
    18: {"activity": VacuumActivity.PAUSED, "slug": "mapping_pause", "is_idle": False},
    19: {
        "activity": VacuumActivity.PAUSED,
        "slug": "go_charge_break",
        "is_idle": False,
    },
    20: {"activity": VacuumActivity.PAUSED, "slug": "wash_break", "is_idle": False},
    21: {
        "activity": VacuumActivity.RETURNING,
        "slug": "go_charge_building_map",
        "is_idle": False,
    },
}

_D109GL = ModelSpec(
    model="xiaomi.vacuum.d109gl",
    name="Xiaomi Robot Vacuum X20 Max",
    property_mapping=_D109_PROPERTY_MAPPING,
    actions=_D109_ACTIONS,
    status=_D109_STATUS,
    fan_speeds=dict(_FAN_SPEEDS),
    sweep_mop_types=dict(_SWEEP_MOP_TYPES),
    clean_times={
        "one_time": 1,
        "two_times": 2,
        "three_times": 3,  # spec v2 adds a third repetition
    },
    mop_water_levels=dict(_MOP_WATER_LEVELS_D109),
    send_commands={
        "start_only_sweep": _D109_ACTIONS.start_only_sweep,
        "start_mop": _D109_ACTIONS.start_mop,
        "start_sweep_mop": _D109_ACTIONS.start_sweep_mop,
        "continue_sweep": _D109_ACTIONS.continue_sweep,
        "start_mop_wash": _cast_action(_D109_ACTIONS.start_mop_wash),
        "stop_mop_wash": _cast_action(_D109_ACTIONS.stop_mop_wash),
        "start_dry": _cast_action(_D109_ACTIONS.start_dry),
        "stop_dry": _cast_action(_D109_ACTIONS.stop_dry),
    },
    fault_kind="ids",
    room_clean_strategy="direct",
)

# --------------------------------------------------------------------------- #
# Xiaomi Robot Vacuum S20+ — xiaomi.vacuum.b108gl (spec v1)
# --------------------------------------------------------------------------- #
#
# Notable differences from d109gl:
# - status is piid 1 (not 2); fault is a plain uint32 on piid 2 (no fault-ids list)
# - continue-sweep and find-vacuum (identify) live in the vacuum-extend service
#   (SIID 6), not the vacuum service (SIID 2)
# - return-home is the battery service's start-charge action (SIID 3 / aiid 1)
# - room sweep input is piid 13 (not 15); room-info lives on SIID 6 / piid 10
# - consumables sit one service lower and report on piid 2 (life-level), not piid 1
# - no auto-wash dock: no dust-arrest / mop-wash / dry actions
# - no sweep-route or obstacle-avoidance-strategy properties
# - only 10 status codes (d109gl has 21)

_B108_PROPERTY_MAPPING: dict[Property, MiotPropertyAddress] = {
    Property.STATUS: {"siid": 2, "piid": 1},
    # Plain uint32 fault; 0 == healthy. fault_kind="simple" reads it directly.
    Property.FAULT: {"siid": 2, "piid": 2},
    Property.SWEEP_MOP_TYPE: {"siid": 2, "piid": 3},
    Property.CLEANING_AREA: {"siid": 2, "piid": 5},
    Property.CLEANING_TIME: {"siid": 2, "piid": 6},
    Property.CLEAN_TIMES: {"siid": 2, "piid": 7},
    Property.FAN_SPEED: {"siid": 2, "piid": 8},
    Property.MOP_WATER_LEVEL: {"siid": 2, "piid": 9},
    # room-info is published by the vacuum-extend service on the S20+.
    Property.ROOM_INFORMATION: {"siid": 6, "piid": 10},
    Property.MAP_OBJ_NAME: {"siid": 7, "piid": 1},
    Property.BATTERY_LEVEL: {"siid": 3, "piid": 1},
    Property.CHARGING_STATE: {"siid": 3, "piid": 2},
    # Consumables: life-level is piid 2 on the S20+ (piid 1 is left-time).
    Property.MOP_LIFE: {"siid": 11, "piid": 2},
    Property.MAIN_BRUSH_LIFE: {"siid": 8, "piid": 2},
    Property.SIDE_BRUSH_LIFE: {"siid": 9, "piid": 2},
    Property.FILTER_LIFE: {"siid": 10, "piid": 2},
}

_B108_ACTIONS = ModelActions(
    start_sweep={"siid": 2, "aiid": 1},
    # "stop-sweeping" on the S20+ is labeled 停止回充 (stop AND return to charge);
    # it doubles as the stop+return behavior the HA STOP button expects.
    stop_sweeping={"siid": 2, "aiid": 2},
    return_home={"siid": 3, "aiid": 1},  # battery.start-charge
    start_only_sweep={"siid": 2, "aiid": 3},
    start_mop={"siid": 2, "aiid": 4},
    start_sweep_mop={"siid": 2, "aiid": 5},
    pause_sweeping={"siid": 2, "aiid": 6},
    continue_sweep={"siid": 6, "aiid": 1},  # vacuum-extend.continue-sweep
    identify={"siid": 6, "aiid": 6},  # vacuum-extend.find-vacuum
    # Room cleaning on the S20+ is a two-step flow (captured from the Mi Home
    # app): mark the target rooms via set-room-clean-configs, then fire
    # start-custom-sweep. There is no direct start-vacuum-room-sweep action the
    # device honours — that action exists in the spec (aiid 13) but the robot
    # ignores it and returns to the dock.
    set_room_clean_configs={"siid": 2, "aiid": 10},
    start_custom_sweep={"siid": 6, "aiid": 7},  # vacuum-extend.start-custom-sweep
)

# is_idle = parked at the dock and safe to start a fresh clean from (1 Idle,
# 2 Charging, 8 Charged).
_B108_STATUS: dict[int, StatusDef] = {
    1: {"activity": VacuumActivity.IDLE, "slug": "idle", "is_idle": True},
    2: {"activity": VacuumActivity.DOCKED, "slug": "charging", "is_idle": True},
    3: {"activity": VacuumActivity.DOCKED, "slug": "break_charging", "is_idle": False},
    4: {"activity": VacuumActivity.CLEANING, "slug": "sweeping", "is_idle": False},
    5: {"activity": VacuumActivity.PAUSED, "slug": "paused", "is_idle": False},
    6: {"activity": VacuumActivity.RETURNING, "slug": "go_charging", "is_idle": False},
    7: {"activity": VacuumActivity.CLEANING, "slug": "remote", "is_idle": False},
    8: {"activity": VacuumActivity.DOCKED, "slug": "charged", "is_idle": True},
    9: {"activity": VacuumActivity.CLEANING, "slug": "building_map", "is_idle": False},
    10: {"activity": VacuumActivity.IDLE, "slug": "updating", "is_idle": False},
}

_B108GL = ModelSpec(
    model="xiaomi.vacuum.b108gl",
    name="Xiaomi Robot Vacuum S20+",
    property_mapping=_B108_PROPERTY_MAPPING,
    actions=_B108_ACTIONS,
    status=_B108_STATUS,
    fan_speeds=dict(_FAN_SPEEDS),
    sweep_mop_types=dict(_SWEEP_MOP_TYPES),
    clean_times=dict(_CLEAN_TIMES),
    mop_water_levels=dict(_MOP_WATER_LEVELS_B108),
    send_commands={
        "start_only_sweep": _B108_ACTIONS.start_only_sweep,
        "start_mop": _B108_ACTIONS.start_mop,
        "start_sweep_mop": _B108_ACTIONS.start_sweep_mop,
        "continue_sweep": _B108_ACTIONS.continue_sweep,
    },
    fault_kind="simple",
    room_clean_strategy="config_then_custom",
)

# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

MODELS: dict[str, ModelSpec] = {
    _D109GL.model: _D109GL,
    _B108GL.model: _B108GL,
}

#: Tuple form for documentation / discovery-side checks.
SUPPORTED_MODELS: tuple[str, ...] = tuple(MODELS)

#: Fallback when neither the live handshake nor the cached snapshot supplies a
#: model (kept as the historical primary model).
DEFAULT_MODEL: str = _D109GL.model

#: Status-code -> slug table shared by both models for the charging-state
#: property (both specs publish the same three values).
CHARGING_STATE_SLUGS: dict[int, str] = dict(_CHARGING_STATE_SLUGS)

#: Sweep-route enumeration (X20 Max only); kept module-level so the select can
#: stay a thin class even when it is never instantiated on the S20+.
SWEEP_ROUTES: dict[str, int] = dict(_SWEEP_ROUTES)
SWEEP_ROUTE_NAMES: dict[int, str] = {v: k for k, v in _SWEEP_ROUTES.items()}

#: Obstacle-avoidance enumeration (X20 Max only).
OBSTACLE_AVOIDANCES: dict[str, int] = dict(_OBSTACLE_AVOIDANCES)
OBSTACLE_AVOIDANCE_NAMES: dict[int, str] = {
    v: k for k, v in _OBSTACLE_AVOIDANCES.items()
}


def get_spec(model: str | None) -> ModelSpec:
    """
    Resolve the spec for a model string, falling back to the default.

    An unknown model logs a warning and falls back to the X20 Max spec so that
    setup never hard-fails on a model we simply have not been added yet; the
    behaviour may be partially wrong but local control stays usable.
    """
    if model and model in MODELS:
        return MODELS[model]
    # Imported lazily to avoid a circular import at module load.
    from .const import LOGGER  # noqa: PLC0415

    LOGGER.warning(
        "Unknown vacuum model %r; falling back to %s. Open an issue if a new "
        "model needs to be added.",
        model,
        DEFAULT_MODEL,
    )
    return MODELS[DEFAULT_MODEL]
