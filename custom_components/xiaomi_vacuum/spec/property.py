"""Symbolic names for the MIoT properties the integration reads."""

from __future__ import annotations

from enum import StrEnum


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
    MOP_STATUS = "mop_status"
    MOP_LIFE = "mop_life"
    MAIN_BRUSH_LIFE = "main_brush_life"
    SIDE_BRUSH_LIFE = "side_brush_life"
    FILTER_LIFE = "filter_life"
