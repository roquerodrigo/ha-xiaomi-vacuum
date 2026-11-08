"""Stable names for the device status codes, shared by every model."""

from __future__ import annotations

from enum import StrEnum


class StatusSlug(StrEnum):
    """
    What a device status code means, independent of the code's number.

    Models number their statuses differently, but every code means one of these;
    the value is the translation key of the status sensor's state.
    """

    BREAK_CHARGING = "break_charging"
    BUILDING_MAP = "building_map"
    CHARGED = "charged"
    CHARGING = "charging"
    DRYING = "drying"
    DUST_COLLECTING = "dust_collecting"
    ERROR = "error"
    GO_CHARGE_BREAK = "go_charge_break"
    GO_CHARGE_BUILDING_MAP = "go_charge_building_map"
    GO_CHARGE_IN_STATION_ASSISTING_CLEANING = "go_charge_in_station_assisting_cleaning"
    GO_CHARGING = "go_charging"
    GO_WASH = "go_wash"
    IDLE = "idle"
    MAPPING_PAUSE = "mapping_pause"
    MOPPING = "mopping"
    MULTI_TASK_RECHARGE = "multi_task_recharge"
    MULTI_TASK_STATION_WORKING = "multi_task_station_working"
    PAUSED = "paused"
    REMOTE = "remote"
    STATION_ASSISTING_CLEANED = "station_assisting_cleaned"
    STATION_ASSISTING_CLEANING = "station_assisting_cleaning"
    STATION_WORKING = "station_working"
    SWEEPING = "sweeping"
    SWEEPING_AND_MOPPING = "sweeping_and_mopping"
    UPDATING = "updating"
    WASH_BREAK = "wash_break"
    WASHING_PAUSED = "washing_paused"
    WATER_INSPECTING = "water_inspecting"
