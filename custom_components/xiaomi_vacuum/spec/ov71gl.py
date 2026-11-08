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
- taking the water tank or dust bin out raises 210020 / 210005, which
  ``_NOTICE_FAULTS`` keeps on the error sensors without forcing ERROR
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
from .model_actions import ModelActions, _require_action
from .model_spec import ModelSpec
from .property import Property
from .status_slug import StatusSlug

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

# Codes 22-24 are the station-assisted washing cycle the S40 Pro adds over the
# X20 Max: rinsing at the dock, rinse finished, returning to the dock to rinse.
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
    22: StatusSlug.STATION_ASSISTING_CLEANING,
    23: StatusSlug.STATION_ASSISTING_CLEANED,
    24: StatusSlug.GO_CHARGE_IN_STATION_ASSISTING_CLEANING,
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

# Maintenance notices the S40 Pro publishes in `Fault Ids` while the user
# services it, cleared on their own once the part is back in place: 210020 when
# the water tank is taken out to be refilled, 210005 when the dust bin is taken
# out to be emptied. Observed on a physical unit.
_NOTICE_FAULTS = frozenset({210005, 210020})

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
        "start_only_sweep": _require_action(
            _ACTIONS.start_only_sweep, "start_only_sweep"
        ),
        "start_mop": _require_action(_ACTIONS.start_mop, "start_mop"),
        "start_sweep_mop": _require_action(_ACTIONS.start_sweep_mop, "start_sweep_mop"),
        "continue_sweep": _ACTIONS.continue_sweep,
    },
    fault_kind="ids",
    room_clean_strategy="direct",
    sweep_routes=dict(SWEEP_ROUTES),
    obstacle_avoidances=dict(OBSTACLE_AVOIDANCES),
    ignored_fault_codes=_PHANTOM_FAULTS,
    notice_fault_codes=_NOTICE_FAULTS,
)
