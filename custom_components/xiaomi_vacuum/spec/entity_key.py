"""Stable keys identifying every entity the integration can create."""

from __future__ import annotations

from enum import StrEnum


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
    MOP_PAD_SENSOR = "mop_pad"
    MAP_IMAGE = "map"
    SWEEP_MOP_TYPE_SELECT = "sweep_mop_type"
    CLEAN_TIMES_SELECT = "clean_times"
    MOP_WATER_LEVEL_SELECT = "mop_water_level"
    SWEEP_ROUTE_SELECT = "sweep_route"
    OBSTACLE_AVOIDANCE_SELECT = "obstacle_avoidance_strategy"
    DUST_ARREST_BUTTON = "dust_arrest"
