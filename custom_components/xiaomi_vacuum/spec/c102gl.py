"""
Spec for the Xiaomi Robot Vacuum X20+ — ``xiaomi.vacuum.c102gl``.

Source: ``urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-c102gl:1``, checked
against a live unit (firmware 4.5.6_1087) in every robot state.

The X20+ is built by Dreame and runs Dreame firmware behind a Xiaomi spec, so
its layout shares almost nothing with the in-house models:

- the vacuum service (SIID 2) holds status, fault and fan speed only; the job
  data, mop settings and task status live in the Dreame service (SIID 4)
- fault is a small Dreame code on a plain uint8 (``fault_kind="simple"``), not
  a Xiaomi six-digit id
- pause is ``stop-sweeping`` (2/2); stop is the Dreame ``stop-clean`` (4/2); a
  paused job resumes through ``start-sweep`` again
- no mode-specific start actions: a clean runs in the mode selected in the app,
  which the firmware packs into the clean-setting bitfield (4.23, bits 0-1)
  together with the wash frequency and water level, so there is no sweep/mop
  type or clean-times select yet
- task status (4.7) stays non-zero for the whole job, mid-job washes and
  recharges included, so it decides the cleaning job and blocks fresh starts
- the status follows the selected mode while cleaning: 1 sweep only, 7 mop
  only, 12 sweep and mop
- room cleaning and the map use Dreame formats and are not wired yet
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.vacuum.const import VacuumActivity

from .cleaning_job_signal import CleaningJobSignal
from .model_actions import ModelActions, _require_action
from .model_spec import ModelSpec, StatusDef
from .property import Property

if TYPE_CHECKING:
    from .addresses import MiotPropertyAddress

_PROPERTY_MAPPING: dict[Property, MiotPropertyAddress] = {
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
)

# Canonical code per activity first (status_code_for): 1 CLEANING, 2 IDLE,
# 3 PAUSED, 5 RETURNING, 6 DOCKED. Charging (6), Go Charging (5) and Washing (9)
# occur both inside a job and after it; the task status settles those, so the
# signals below only matter until it has been polled. They match the slugs'
# signals on the other models.
_STATUS: dict[int, StatusDef] = {
    1: {
        "activity": VacuumActivity.CLEANING,
        "slug": "sweeping",
        "is_idle": False,
        "cleaning_job": CleaningJobSignal.IN_PROGRESS,
    },
    2: {
        "activity": VacuumActivity.IDLE,
        "slug": "idle",
        "is_idle": True,
        "cleaning_job": CleaningJobSignal.FINISHED,
    },
    3: {
        "activity": VacuumActivity.PAUSED,
        "slug": "paused",
        "is_idle": False,
        "cleaning_job": CleaningJobSignal.IN_PROGRESS,
    },
    5: {
        "activity": VacuumActivity.RETURNING,
        "slug": "go_charging",
        "is_idle": False,
        "cleaning_job": CleaningJobSignal.FINISHED,
    },
    6: {
        "activity": VacuumActivity.DOCKED,
        "slug": "charging",
        "is_idle": True,
        "cleaning_job": CleaningJobSignal.FINISHED,
    },
    # The ERROR activity comes from an active fault, never from the status.
    4: {
        "activity": VacuumActivity.IDLE,
        "slug": "error",
        "is_idle": False,
        "cleaning_job": CleaningJobSignal.INCONCLUSIVE,
    },
    7: {
        "activity": VacuumActivity.CLEANING,
        "slug": "mopping",
        "is_idle": False,
        "cleaning_job": CleaningJobSignal.IN_PROGRESS,
    },
    8: {
        "activity": VacuumActivity.DOCKED,
        "slug": "drying",
        "is_idle": True,
        "cleaning_job": CleaningJobSignal.FINISHED,
    },
    # Mop wash in the dock: before leaving, between rooms and after the job.
    9: {
        "activity": VacuumActivity.DOCKED,
        "slug": "go_wash",
        "is_idle": False,
        "cleaning_job": CleaningJobSignal.INCONCLUSIVE,
    },
    # Driving back to wash the mops mid-job.
    10: {
        "activity": VacuumActivity.RETURNING,
        "slug": "wash_break",
        "is_idle": False,
        "cleaning_job": CleaningJobSignal.IN_PROGRESS,
    },
    11: {
        "activity": VacuumActivity.CLEANING,
        "slug": "building_map",
        "is_idle": False,
        "cleaning_job": CleaningJobSignal.IN_PROGRESS,
    },
    12: {
        "activity": VacuumActivity.CLEANING,
        "slug": "sweeping_and_mopping",
        "is_idle": False,
        "cleaning_job": CleaningJobSignal.IN_PROGRESS,
    },
    13: {
        "activity": VacuumActivity.DOCKED,
        "slug": "charged",
        "is_idle": True,
        "cleaning_job": CleaningJobSignal.FINISHED,
    },
    14: {
        "activity": VacuumActivity.IDLE,
        "slug": "updating",
        "is_idle": False,
        "cleaning_job": CleaningJobSignal.FINISHED,
    },
    19: {
        "activity": VacuumActivity.DOCKED,
        "slug": "water_inspecting",
        "is_idle": False,
        "cleaning_job": CleaningJobSignal.INCONCLUSIVE,
    },
    21: {
        "activity": VacuumActivity.PAUSED,
        "slug": "washing_paused",
        "is_idle": False,
        "cleaning_job": CleaningJobSignal.IN_PROGRESS,
    },
    22: {
        "activity": VacuumActivity.DOCKED,
        "slug": "dust_collecting",
        "is_idle": False,
        "cleaning_job": CleaningJobSignal.INCONCLUSIVE,
    },
    23: {
        "activity": VacuumActivity.CLEANING,
        "slug": "remote",
        "is_idle": False,
        "cleaning_job": CleaningJobSignal.IN_PROGRESS,
    },
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
    sweep_mop_types={},
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
    fault_kind="simple",
    room_clean_strategy="none",
    # Routine prompts, not faults:
    # - 68 is published while the robot sits in the dock with its mop pads on
    #   (fully charged, drying) and clears as soon as it leaves or the pads
    #   come off;
    # - 114 asks to rinse the dock's mop-washing tray after a mop job, seen
    #   while drying.
    notice_fault_codes=frozenset({68, 114}),
)
