"""
Spec for the Xiaomi Robot Vacuum S40 Pro — ``xiaomi.vacuum.ov71gl``.

Source: ``urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-ov71gl:1`` (the only
published revision). The S40 Pro is an export-only product: its spec is not
served by the Mainland China cloud, so the config flow must use another region
(Europe for EU units) for the vacuum to be discovered.

The vacuum-service layout is the X20 Max's (``d109gl.py``): every SIID/PIID/AIID
this integration reads or invokes is identical. Where the two diverge:

- status publishes three extra codes (22 StationAssistingCleaning, 23
  StationAssistingCleaned, 24 GoChargeInStationAssistingCleaning)
- the retail S40 Pro ships with a plain charging dock. The spec template still
  lists dust-arrest / mop-wash actions, but no dock hardware honours them, so no
  dock action is wired: no dust-arrest button, no mop-wash / dry send_commands
- no detergent (SIID 18) or dust-bag (SIID 19) services, no start-dry action
- the dockless hardware still runs the station's sewage-tank check and reports
  its permanent failure as fault 100027, which ``_PHANTOM_FAULTS`` drops
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
from .model_actions import ModelActions
from .model_spec import ModelSpec, StatusDef
from .property import Property

if TYPE_CHECKING:
    from .addresses import MiotPropertyAddress

_PROPERTY_MAPPING: dict[Property, MiotPropertyAddress] = {
    Property.STATUS: {"siid": 2, "piid": 2},
    # Live fault state: Fault Ids (piid 66) is the live {"fault": [codes]} list
    # ([0] = none). Device Fault (piid 3) latches the last code, like the X20 Max.
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
    continue_sweep={"siid": 2, "aiid": 8},
    start_room_sweep={"siid": 2, "aiid": 16, "in_piid": 15},
    identify={"siid": 6, "aiid": 1},
)

# The ERROR activity is NOT produced from status: an active fault drives it (see
# XiaomiVacuum.activity). Break/interrupt statuses and the bare "Error" status
# (15) occur with no active fault during normal cycles, so they map to their
# nearest non-error activity. Codes 22-24 are the station-assisted cleaning
# cycle the S40 Pro adds over the X20 Max.
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
    22: {
        "activity": VacuumActivity.CLEANING,
        "slug": "station_assisting_cleaning",
        "is_idle": False,
    },
    23: {
        "activity": VacuumActivity.DOCKED,
        "slug": "station_assisting_cleaned",
        "is_idle": False,
    },
    24: {
        "activity": VacuumActivity.RETURNING,
        "slug": "go_charge_in_station_assisting_cleaning",
        "is_idle": False,
    },
}

# Fault codes the S40 Pro reports permanently for dock hardware it does not
# have. 100027 ("Sewage tank is full or not installed") is published in the live
# `Fault Ids` list from boot and never clears: the firmware is shared with the
# station-equipped variants of the family and keeps running the sewage-tank
# check, while the retail S40 Pro ships with a plain charging dock that has no
# sewage tank at all. The Mi Home app knows the dock type and shows nothing, so
# the integration must drop the code too — otherwise the vacuum entity is stuck
# in ERROR forever. Observed on a physical unit, firmware 4.5.8_0053, docked and
# fully charged (status 9).
_PHANTOM_FAULTS = frozenset({100027})

OV71GL = ModelSpec(
    model="xiaomi.vacuum.ov71gl",
    name="Xiaomi Robot Vacuum S40 Pro",
    property_mapping=_PROPERTY_MAPPING,
    actions=_ACTIONS,
    status=_STATUS,
    fan_speeds=dict(FAN_SPEEDS),
    sweep_mop_types=dict(SWEEP_MOP_TYPES),
    clean_times={
        "one_time": 1,
        "two_times": 2,
        "three_times": 3,
    },
    mop_water_levels={
        "off": 0,
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
    },
    fault_kind="ids",
    room_clean_strategy="direct",
    sweep_routes=dict(SWEEP_ROUTES),
    obstacle_avoidances=dict(OBSTACLE_AVOIDANCES),
    ignored_fault_codes=_PHANTOM_FAULTS,
)
