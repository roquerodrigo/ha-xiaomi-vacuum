"""Constants for xiaomi_vacuum (xiaomi.vacuum.d109gl MIoT spec v2)."""

from __future__ import annotations

from logging import Logger, getLogger

from homeassistant.components.vacuum import VacuumActivity

LOGGER: Logger = getLogger(__package__)

DOMAIN = "xiaomi_vacuum"
ATTRIBUTION = ""
MODEL = "xiaomi.vacuum.d109gl"

CONF_HOST = "host"
CONF_TOKEN = "token"  # noqa: S105
CONF_NAME = "name"

ENV_HOST = "XIAOMI_VACUUM_HOST"
ENV_TOKEN = "XIAOMI_VACUUM_TOKEN"  # noqa: S105
ENV_NAME = "XIAOMI_VACUUM_NAME"

PROPERTY_MAPPING: dict[str, dict[str, int]] = {
    "status": {"siid": 2, "piid": 2},
    "fault": {"siid": 2, "piid": 3},
    "sweep_mop_type": {"siid": 2, "piid": 4},
    "cleaning_area": {"siid": 2, "piid": 6},
    "cleaning_time": {"siid": 2, "piid": 7},
    "clean_times": {"siid": 2, "piid": 8},
    "fan_speed": {"siid": 2, "piid": 9},
    "mop_water_level": {"siid": 2, "piid": 10},
    "room_information": {"siid": 2, "piid": 16},
    "last_clean_time": {"siid": 2, "piid": 17},
    "sweep_route": {"siid": 2, "piid": 74},
    "obstacle_avoidance_strategy": {"siid": 2, "piid": 75},
    "battery_level": {"siid": 3, "piid": 1},
    "charging_state": {"siid": 3, "piid": 2},
}

ACTION_START_SWEEP = {"siid": 2, "aiid": 1}
ACTION_STOP_SWEEPING = {"siid": 2, "aiid": 2}
ACTION_RETURN_HOME = {"siid": 2, "aiid": 3}
ACTION_PAUSE_SWEEPING = {"siid": 2, "aiid": 7}
ACTION_START_ROOM_SWEEP = {"siid": 2, "aiid": 16, "in_piid": 15}
ACTION_START_DUST_ARREST = {"siid": 2, "aiid": 18}
ACTION_IDENTIFY = {"siid": 6, "aiid": 1}

STATUS_TO_ACTIVITY: dict[int, VacuumActivity] = {
    1: VacuumActivity.IDLE,
    2: VacuumActivity.DOCKED,
    3: VacuumActivity.ERROR,
    4: VacuumActivity.CLEANING,
    5: VacuumActivity.PAUSED,
    6: VacuumActivity.RETURNING,
    7: VacuumActivity.RETURNING,
    8: VacuumActivity.CLEANING,
    9: VacuumActivity.DOCKED,
    10: VacuumActivity.CLEANING,
    11: VacuumActivity.IDLE,
    12: VacuumActivity.DOCKED,
    13: VacuumActivity.RETURNING,
    14: VacuumActivity.DOCKED,
    15: VacuumActivity.ERROR,
    16: VacuumActivity.CLEANING,
    17: VacuumActivity.CLEANING,
    18: VacuumActivity.PAUSED,
    19: VacuumActivity.ERROR,
    20: VacuumActivity.ERROR,
    21: VacuumActivity.RETURNING,
}

STATUS_SLUGS: dict[int, str] = {
    1: "idle",
    2: "charging",
    3: "break_charging",
    4: "sweeping",
    5: "paused",
    6: "go_charging",
    7: "go_wash",
    8: "remote",
    9: "charged",
    10: "building_map",
    11: "updating",
    12: "multi_task_station_working",
    13: "multi_task_recharge",
    14: "station_working",
    15: "error",
    16: "sweeping_and_mopping",
    17: "mopping",
    18: "mapping_pause",
    19: "go_charge_break",
    20: "wash_break",
    21: "go_charge_building_map",
}

FAN_SPEEDS: dict[str, int] = {
    "silent": 1,
    "basic": 2,
    "strong": 3,
    "full_speed": 4,
}
FAN_SPEED_NAMES: dict[int, str] = {v: k for k, v in FAN_SPEEDS.items()}

SWEEP_MOP_TYPES: dict[str, int] = {
    "sweep": 1,
    "mop": 2,
    "sweep_mop": 3,
    "sweep_before_mopping": 4,
}
SWEEP_MOP_TYPE_NAMES: dict[int, str] = {v: k for k, v in SWEEP_MOP_TYPES.items()}

CLEAN_TIMES: dict[str, int] = {
    "one_time": 1,
    "two_times": 2,
}
CLEAN_TIMES_NAMES: dict[int, str] = {v: k for k, v in CLEAN_TIMES.items()}

MOP_WATER_LEVELS: dict[str, int] = {
    "level_1": 1,
    "level_2": 2,
    "level_3": 3,
}
MOP_WATER_LEVEL_NAMES: dict[int, str] = {v: k for k, v in MOP_WATER_LEVELS.items()}

SWEEP_ROUTES: dict[str, int] = {
    "quick": 1,
    "daily": 2,
    "careful": 3,
}
SWEEP_ROUTE_NAMES: dict[int, str] = {v: k for k, v in SWEEP_ROUTES.items()}

OBSTACLE_AVOIDANCES: dict[str, int] = {
    "less_collisions": 0,
    "high_coverage": 1,
}
OBSTACLE_AVOIDANCE_NAMES: dict[int, str] = {
    v: k for k, v in OBSTACLE_AVOIDANCES.items()
}

CHARGING_STATE_SLUGS: dict[int, str] = {
    1: "charging",
    2: "not_charging",
    3: "not_chargeable",
}
