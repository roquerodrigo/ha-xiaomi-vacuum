"""
Spec for the Xiaomi Robot Vacuum S20+ — ``xiaomi.vacuum.b108gl``.

Source: ``urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-b108gl:1``.

Notable differences from the X20 Max (``d109gl``):

- status is piid 1 (not 2); fault is a plain uint32 on piid 2 (no fault-ids list)
- continue-sweep and find-vacuum (identify) live in the vacuum-extend service
  (SIID 6), not the vacuum service (SIID 2)
- return-home is the battery service's start-charge action (SIID 3 / aiid 1)
- room sweep input is piid 13 (not 15); room-info lives on SIID 6 / piid 10
- consumables sit one service lower and report on piid 2 (life-level), not piid 1
- no auto-wash dock: no dust-arrest / mop-wash / dry actions
- no sweep-route or obstacle-avoidance-strategy properties
- only 10 status codes (the X20 Max has 21)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.vacuum.const import VacuumActivity

from .enumerations import (
    CHARGING_STATE_SLUGS,
    CLEAN_TIMES,
    FAN_SPEEDS,
    SWEEP_MOP_TYPES,
)
from .model_actions import ModelActions
from .model_spec import ModelSpec, StatusDef
from .property import Property

if TYPE_CHECKING:
    from .addresses import MiotPropertyAddress

_PROPERTY_MAPPING: dict[Property, MiotPropertyAddress] = {
    Property.STATUS: {"siid": 2, "piid": 1},
    # Plain uint32 fault; 0 == healthy. fault_kind="simple" reads it directly.
    Property.FAULT: {"siid": 2, "piid": 2},
    Property.SWEEP_MOP_TYPE: {"siid": 2, "piid": 3},
    Property.CLEANING_AREA: {"siid": 2, "piid": 5},
    Property.CLEANING_TIME: {"siid": 2, "piid": 6},
    Property.CLEAN_TIMES: {"siid": 2, "piid": 7},
    Property.FAN_SPEED: {"siid": 2, "piid": 8},
    Property.MOP_WATER_LEVEL: {"siid": 2, "piid": 9},
    # mop-status is published by the vacuum-extend service on the S20+.
    Property.MOP_STATUS: {"siid": 6, "piid": 1},
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

_ACTIONS = ModelActions(
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
_STATUS: dict[int, StatusDef] = {
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

B108GL = ModelSpec(
    model="xiaomi.vacuum.b108gl",
    name="Xiaomi Robot Vacuum S20+",
    property_mapping=_PROPERTY_MAPPING,
    actions=_ACTIONS,
    status=_STATUS,
    fan_speeds=dict(FAN_SPEEDS),
    sweep_mop_types=dict(SWEEP_MOP_TYPES),
    clean_times=dict(CLEAN_TIMES),
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
    fault_kind="simple",
    room_clean_strategy="config_then_custom",
)
