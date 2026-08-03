"""
Spec for the Xiaomi Robot Vacuum X20 Max — ``xiaomi.vacuum.d109gl``.

Source: ``urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-d109gl:2``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.vacuum.const import VacuumActivity

from .enumerations import (
    CHARGING_STATE_SLUGS,
    FAN_SPEEDS,
    OBSTACLE_AVOIDANCES,
    SWEEP_MOP_TYPES,
    SWEEP_ROUTES,
)
from .model_actions import ModelActions, _require_action
from .model_spec import ModelSpec, StatusDef
from .property import Property

if TYPE_CHECKING:
    from .addresses import MiotPropertyAddress

_PROPERTY_MAPPING: dict[Property, MiotPropertyAddress] = {
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
    Property.MOP_STATUS: {"siid": 2, "piid": 11},
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

_ACTIONS = ModelActions(
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
_STATUS: dict[int, StatusDef] = {
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

D109GL = ModelSpec(
    model="xiaomi.vacuum.d109gl",
    name="Xiaomi Robot Vacuum X20 Max",
    property_mapping=_PROPERTY_MAPPING,
    actions=_ACTIONS,
    status=_STATUS,
    fan_speeds=dict(FAN_SPEEDS),
    sweep_mop_types=dict(SWEEP_MOP_TYPES),
    clean_times={
        "one_time": 1,
        "two_times": 2,
        "three_times": 3,  # spec v2 adds a third repetition
    },
    mop_water_levels={
        "level_1": 1,
        "level_2": 2,
        "level_3": 3,
    },
    charging_state_slugs=dict(CHARGING_STATE_SLUGS),
    send_commands={
        "start_only_sweep": _ACTIONS.start_only_sweep,
        "start_mop": _ACTIONS.start_mop,
        "start_sweep_mop": _ACTIONS.start_sweep_mop,
        "continue_sweep": _ACTIONS.continue_sweep,
        "start_mop_wash": _require_action(_ACTIONS.start_mop_wash, "start_mop_wash"),
        "stop_mop_wash": _require_action(_ACTIONS.stop_mop_wash, "stop_mop_wash"),
        "start_dry": _require_action(_ACTIONS.start_dry, "start_dry"),
        "stop_dry": _require_action(_ACTIONS.stop_dry, "stop_dry"),
    },
    fault_kind="ids",
    room_clean_strategy="direct",
    sweep_routes=dict(SWEEP_ROUTES),
    obstacle_avoidances=dict(OBSTACLE_AVOIDANCES),
)
