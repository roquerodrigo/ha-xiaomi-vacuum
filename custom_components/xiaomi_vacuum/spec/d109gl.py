"""
Spec for the Xiaomi Robot Vacuum X20 Max — ``xiaomi.vacuum.d109gl``.

Source: ``urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-d109gl:2``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .enumerations import (
    CHARGING_STATE_SLUGS,
    FAN_SPEEDS,
    OBSTACLE_AVOIDANCES,
    SWEEP_MOP_TYPES,
    SWEEP_ROUTES,
)
from .model_actions import ModelActions
from .model_spec import ModelSpec
from .property import Property
from .room_cleaning import DirectRoomSweep
from .status_slug import StatusSlug

if TYPE_CHECKING:
    from .addresses import MiotPropertyBinding

_PROPERTY_MAPPING: dict[Property, MiotPropertyBinding] = {
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
    # Hours left on each consumable, next to its life level.
    Property.MOP_TIME_LEFT: {"siid": 9, "piid": 2},
    Property.MAIN_BRUSH_TIME_LEFT: {"siid": 12, "piid": 2},
    Property.SIDE_BRUSH_TIME_LEFT: {"siid": 13, "piid": 2},
    Property.FILTER_TIME_LEFT: {"siid": 14, "piid": 2},
    # The custom cleanings list grows with every cleaning saved in Mi Home and
    # would push the batched poll reply past the single-datagram limit.
    Property.USER_DEFINE_SWEEP_CONFIG: {"siid": 2, "piid": 42, "polled": False},
    Property.CARPET_BOOST: {"siid": 2, "piid": 20, "boolean": True},
    # "Sweep Break Switch": resume an unfinished job after recharging.
    Property.RESUME_AFTER_CHARGE: {"siid": 2, "piid": 23, "boolean": True},
    Property.CHILD_LOCK: {"siid": 5, "piid": 1, "boolean": True},
    Property.DO_NOT_DISTURB: {"siid": 11, "piid": 1, "boolean": True},
    Property.VOLUME: {"siid": 4, "piid": 2},  # 0-100
    # Dock settings. The area interval is published as "Frequency Mop Wash No
    # Tank", yet it is the one the Mi Home app sets on this tank-fed dock.
    Property.MOP_WASH: {"siid": 2, "piid": 28, "boolean": True},
    Property.MOP_WASH_FREQUENCY: {"siid": 2, "piid": 29},
    Property.MOP_WASH_AREA_INTERVAL: {"siid": 2, "piid": 61},
    Property.MOP_WASH_TIME_INTERVAL: {"siid": 2, "piid": 81},  # minutes
    Property.MOP_DRYING_TIME: {"siid": 2, "piid": 31},
    Property.AUTO_DUST_COLLECTION: {"siid": 2, "piid": 32, "boolean": True},
    Property.AUTO_MOP_DRYING: {"siid": 2, "piid": 34, "boolean": True},
    Property.MOP_WASH_WATER_MODE: {"siid": 2, "piid": 30},
    Property.MOP_WASH_TEMPERATURE: {"siid": 2, "piid": 84},
    Property.DUST_COLLECTION_FREQUENCY: {"siid": 2, "piid": 33},
    Property.CARPET_CLEANING_METHOD: {"siid": 2, "piid": 73},
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
    start_zone_sweep={"siid": 2, "aiid": 37, "in_piid": 12},
    start_user_define_sweep={"siid": 2, "aiid": 42, "in_piid": 43},
    identify={"siid": 6, "aiid": 1},
    start_dust_arrest={"siid": 2, "aiid": 18},
    start_mop_wash={"siid": 2, "aiid": 19},
    start_dry={"siid": 2, "aiid": 20},
    stop_mop_wash={"siid": 2, "aiid": 31},
    stop_dry={"siid": 2, "aiid": 32},
    reset_mop={"siid": 9, "aiid": 1},
    reset_main_brush={"siid": 12, "aiid": 1},
    reset_side_brush={"siid": 13, "aiid": 1},
    reset_filter={"siid": 14, "aiid": 1},
)

# Slugs follow what the robot physically does, as the Mi Home strings describe
# it: 19 GoChargeBreak and 20 WashBreak drive back to the dock mid-job, 7 GoWash
# washes the mop while docked.
_STATUS: dict[int, StatusSlug] = {
    1: StatusSlug.IDLE,
    2: StatusSlug.CHARGING,
    3: StatusSlug.BREAK_CHARGING,
    4: StatusSlug.SWEEPING,
    5: StatusSlug.PAUSED,
    6: StatusSlug.GO_CHARGING,
    7: StatusSlug.GO_WASH,
    8: StatusSlug.REMOTE,
    9: StatusSlug.CHARGED,
    10: StatusSlug.BUILDING_MAP,
    11: StatusSlug.UPDATING,
    12: StatusSlug.MULTI_TASK_STATION_WORKING,
    13: StatusSlug.MULTI_TASK_RECHARGE,
    14: StatusSlug.STATION_WORKING,
    15: StatusSlug.ERROR,
    16: StatusSlug.SWEEPING_AND_MOPPING,
    17: StatusSlug.MOPPING,
    18: StatusSlug.MAPPING_PAUSE,
    19: StatusSlug.GO_CHARGE_BREAK,
    20: StatusSlug.WASH_BREAK,
    21: StatusSlug.GO_CHARGE_BUILDING_MAP,
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
        "off": 0,
        "level_1": 1,
        "level_2": 2,
        "level_3": 3,
    },
    charging_state_slugs=dict(CHARGING_STATE_SLUGS),
    room_cleaning=DirectRoomSweep({"siid": 2, "aiid": 16, "in_piid": 15}),
    sweep_routes=dict(SWEEP_ROUTES),
    obstacle_avoidances=dict(OBSTACLE_AVOIDANCES),
    mop_wash_frequencies={
        "by_room": 0,
        "by_area": 1,
        "by_time": 2,
    },
    # The device numbers the intervals out of order (8 m² is 2); listed by area.
    mop_wash_area_intervals={
        "five_square_meters": 0,
        "eight_square_meters": 2,
        "ten_square_meters": 1,
        "fifteen_square_meters": 3,
        "twenty_square_meters": 4,
        "twenty_five_square_meters": 5,
    },
    mop_drying_times={
        "2_hours": 1,
        "3_hours": 2,
        "4_hours": 3,
    },
    mop_wash_water_modes={
        "deep": 0,
        "daily": 1,
        "save_water": 2,
    },
    mop_wash_temperatures={
        "normal": 0,
        "warm": 1,
        "hot": 2,
        "smart": 3,
    },
    dust_collection_frequencies={
        "once": 1,
        "twice": 2,
        "three_times": 3,
    },
    carpet_cleaning_methods={
        "adaptive": 0,
        "avoid": 1,
        "ignore": 2,
        "cross": 3,
    },
)
