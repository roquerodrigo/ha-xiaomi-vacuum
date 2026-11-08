"""
Spec for the Xiaomi Robot Vacuum X20+ — ``xiaomi.vacuum.c102gl``.

Source: ``urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-c102gl:1``, checked
against a live unit (firmware 4.5.6_1087) in every robot state.

The X20+ is built by Dreame and runs Dreame firmware behind a Xiaomi spec, so
its layout shares almost nothing with the in-house models:

- the vacuum service (SIID 2) holds status, fault and fan speed only; the job
  data, mop settings and task status live in the Dreame service (SIID 4)
- fault is a small Dreame code on a plain uint8, not a Xiaomi six-digit id
- pause is ``stop-sweeping`` (2/2); stop is the Dreame ``stop-clean`` (4/2); a
  paused job resumes through ``start-sweep`` again
- no mode-specific start actions: a clean runs in the selected mode, which the
  firmware packs into the low two bits of the clean-setting bitfield (4.23)
  together with the wash frequency and water level; the mode select reads and
  writes only those bits (the ``mask`` of its binding). There is no clean-times
  property
- task status (4.7) stays non-zero for the whole job, mid-job washes and
  recharges included, so it decides the cleaning job and blocks fresh starts
- the status follows the selected mode while cleaning: 1 sweep only, 7 mop
  only, 12 sweep and mop
- room cleaning goes through the Dreame ``start-clean`` (4/1) with the segment
  work mode; the spec's ``start-room-sweep`` (2/3) is acknowledged but ignored
- the map is a Dreame blob (``map_format="dreame"``): the SDK's Dreame decoder
  draws it and its segment metadata gives the room list
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .map_format import DreameMapFormat
from .model_actions import ModelActions, _require_action
from .model_spec import ModelSpec
from .property import Property
from .room_cleaning import DreameSegmentClean
from .status_slug import StatusSlug

if TYPE_CHECKING:
    from .addresses import MiotPropertyBinding

_PROPERTY_MAPPING: dict[Property, MiotPropertyBinding] = {
    Property.STATUS: {"siid": 2, "piid": 1},
    # Plain uint8 Dreame fault code; 0 == healthy.
    Property.FAULT: {"siid": 2, "piid": 2},
    Property.FAN_SPEED: {"siid": 2, "piid": 3},
    Property.BATTERY_LEVEL: {"siid": 3, "piid": 1},
    Property.CHARGING_STATE: {"siid": 3, "piid": 2},
    # Current job; they keep the last job's values while docked.
    Property.CLEANING_TIME: {"siid": 4, "piid": 2},
    Property.CLEANING_AREA: {"siid": 4, "piid": 3},
    Property.MOP_WATER_LEVEL: {"siid": 4, "piid": 5},
    # waterbox-status tracks the mop pads on this model: it drops to 0 when the
    # pads are taken off. mop-pad-installed (4.53) reads 0 in every state.
    Property.MOP_STATUS: {"siid": 4, "piid": 6},
    Property.TASK_STATUS: {"siid": 4, "piid": 7},
    # Consumables: brush services report the life level on piid 2 (piid 1 is
    # hours left); filter and mop report it on piid 1.
    Property.MAIN_BRUSH_LIFE: {"siid": 9, "piid": 2},
    Property.SIDE_BRUSH_LIFE: {"siid": 10, "piid": 2},
    Property.FILTER_LIFE: {"siid": 11, "piid": 1},
    Property.MOP_LIFE: {"siid": 18, "piid": 1},
    # {"object_name": ..., "md5": ...} of the current map in the Xiaomi cloud.
    Property.MAP_OBJ_NAME: {"siid": 6, "piid": 8},
    # Cleaning mode: low two bits of the Dreame clean-setting, packed with the
    # wash frequency and water level. The spec lists 4.23 without access, but
    # the firmware accepts writes.
    Property.SWEEP_MOP_TYPE: {"siid": 4, "piid": 23, "mask": 0x03},
    # Hours left on each consumable (the life level is on the sibling piid).
    Property.MAIN_BRUSH_TIME_LEFT: {"siid": 9, "piid": 1},
    Property.SIDE_BRUSH_TIME_LEFT: {"siid": 10, "piid": 1},
    Property.FILTER_TIME_LEFT: {"siid": 11, "piid": 2},
    Property.MOP_TIME_LEFT: {"siid": 18, "piid": 2},
    # Minutes of mop-pad drying left, 0 when not drying.
    Property.DRYING_TIME_LEFT: {"siid": 2, "piid": 5},
    # Lifetime totals, updated when the robot docks after a job.
    Property.TOTAL_CLEAN_TIME: {"siid": 12, "piid": 2},  # minutes
    Property.TOTAL_CLEAN_COUNT: {"siid": 12, "piid": 3},
    Property.TOTAL_CLEAN_AREA: {"siid": 12, "piid": 4},  # square metres
    # uint8 0/1 switches.
    Property.RESUME_AFTER_CHARGE: {"siid": 4, "piid": 11},
    Property.CARPET_BOOST: {"siid": 4, "piid": 12},
    Property.CHILD_LOCK: {"siid": 4, "piid": 27},
    # The quiet hours themselves are 5.2 / 5.3 ("HH:MM").
    Property.DO_NOT_DISTURB: {"siid": 5, "piid": 1, "boolean": True},
    Property.VOLUME: {"siid": 7, "piid": 1},  # 0-100
}

_ACTIONS = ModelActions(
    start_sweep={"siid": 2, "aiid": 1},
    stop_sweeping={"siid": 4, "aiid": 2},  # Dreame stop-clean: ends the job
    return_home={"siid": 3, "aiid": 1},  # battery.start-charge
    pause_sweeping={"siid": 2, "aiid": 2},  # "stop-sweeping" pauses on Dreame
    continue_sweep={"siid": 2, "aiid": 1},  # start-sweep resumes a paused job
    identify={"siid": 7, "aiid": 1},  # audio.position
    start_dust_arrest={"siid": 2, "aiid": 4},
    start_mop_wash={"siid": 2, "aiid": 6},
    start_dry={"siid": 2, "aiid": 8},
    stop_dry={"siid": 2, "aiid": 9},
    reset_main_brush={"siid": 9, "aiid": 1},
    reset_side_brush={"siid": 10, "aiid": 1},
    reset_filter={"siid": 11, "aiid": 1},
    reset_mop={"siid": 18, "aiid": 1},
)

# Charging (6), Go Charging (5) and Washing (9) occur both inside a job and after
# it; the task status settles those, so the slugs' cleaning-job signals only
# matter until it has been polled. 9 washes the mops in the dock (before leaving,
# between rooms, after the job); 10 drives back to wash them mid-job.
_STATUS: dict[int, StatusSlug] = {
    1: StatusSlug.SWEEPING,
    2: StatusSlug.IDLE,
    3: StatusSlug.PAUSED,
    5: StatusSlug.GO_CHARGING,
    6: StatusSlug.CHARGING,
    4: StatusSlug.ERROR,
    7: StatusSlug.MOPPING,
    8: StatusSlug.DRYING,
    9: StatusSlug.GO_WASH,
    10: StatusSlug.WASH_BREAK,
    11: StatusSlug.BUILDING_MAP,
    12: StatusSlug.SWEEPING_AND_MOPPING,
    13: StatusSlug.CHARGED,
    14: StatusSlug.UPDATING,
    19: StatusSlug.WATER_INSPECTING,
    21: StatusSlug.WASHING_PAUSED,
    22: StatusSlug.DUST_COLLECTING,
    23: StatusSlug.REMOTE,
}

C102GL = ModelSpec(
    model="xiaomi.vacuum.c102gl",
    name="Xiaomi Robot Vacuum X20+",
    property_mapping=_PROPERTY_MAPPING,
    actions=_ACTIONS,
    status=_STATUS,
    # Same four levels as the other models, numbered from 0.
    fan_speeds={
        "silent": 0,
        "basic": 1,
        "strong": 2,
        "full_speed": 3,
    },
    # Low two bits of 4.23; the robot lifts its mops for "sweep" and switches
    # to it by itself when the pads are taken off.
    sweep_mop_types={
        "sweep_mop": 0,
        "mop": 1,
        "sweep": 2,
        "sweep_before_mopping": 3,
    },
    clean_times={},
    # Low / Medium / High; there is no "off" (sweep-only mode lifts the mops).
    mop_water_levels={
        "level_1": 1,
        "level_2": 2,
        "level_3": 3,
    },
    charging_state_slugs={1: "charging", 2: "not_charging", 5: "go_charging"},
    send_commands={
        "continue_sweep": _ACTIONS.continue_sweep,
        "start_mop_wash": _require_action(_ACTIONS.start_mop_wash, "start_mop_wash"),
        "start_dry": _require_action(_ACTIONS.start_dry, "start_dry"),
        "stop_dry": _require_action(_ACTIONS.stop_dry, "stop_dry"),
    },
    # Dreame start-clean: piid 1 work mode, piid 10 clean-extend data.
    room_cleaning=DreameSegmentClean(
        {"siid": 4, "aiid": 1, "mode_piid": 1, "data_piid": 10}
    ),
    # Routine prompts, not faults:
    # - 68 is published while the robot sits in the dock with its mop pads on
    #   (fully charged, drying) and clears as soon as it leaves or the pads
    #   come off;
    # - 114 asks to rinse the dock's mop-washing tray after a mop job, seen
    #   while drying.
    notice_fault_codes=frozenset({68, 114}),
    map_format=DreameMapFormat(),
)
