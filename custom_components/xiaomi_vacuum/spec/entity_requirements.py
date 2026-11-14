"""What each optional entity needs from a model's spec."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING

from .entity_key import EntityKey
from .property import Property

if TYPE_CHECKING:
    from collections.abc import Mapping

#: Entities every vacuum exposes: they derive from the status and the fault,
#: which every model publishes.
BASE_ENTITIES: frozenset[EntityKey] = frozenset(
    {
        EntityKey.VACUUM,
        EntityKey.STATUS_SENSOR,
        EntityKey.ERROR_SENSOR,
        EntityKey.ERROR_CODE_SENSOR,
        EntityKey.CLEANING_SENSOR,
    }
)

#: Entities backed by one property, created only when the model maps it, so a
#: model without e.g. a side brush gets no side-brush sensor stuck at unknown.
PROPERTY_ENTITIES: Mapping[Property, EntityKey] = MappingProxyType(
    {
        Property.BATTERY_LEVEL: EntityKey.BATTERY_SENSOR,
        Property.CHARGING_STATE: EntityKey.BATTERY_CHARGING_SENSOR,
        Property.MOP_LIFE: EntityKey.MOP_LIFE_SENSOR,
        Property.MAIN_BRUSH_LIFE: EntityKey.MAIN_BRUSH_LIFE_SENSOR,
        Property.SIDE_BRUSH_LIFE: EntityKey.SIDE_BRUSH_LIFE_SENSOR,
        Property.FILTER_LIFE: EntityKey.FILTER_LIFE_SENSOR,
        Property.SWEEP_ROUTE: EntityKey.SWEEP_ROUTE_SELECT,
        Property.OBSTACLE_AVOIDANCE_STRATEGY: EntityKey.OBSTACLE_AVOIDANCE_SELECT,
        Property.MAP_OBJ_NAME: EntityKey.MAP_IMAGE,
        Property.MOP_STATUS: EntityKey.MOP_PAD_SENSOR,
        Property.SWEEP_MOP_TYPE: EntityKey.SWEEP_MOP_TYPE_SELECT,
        Property.CLEAN_TIMES: EntityKey.CLEAN_TIMES_SELECT,
        Property.MOP_WATER_LEVEL: EntityKey.MOP_WATER_LEVEL_SELECT,
        Property.MAIN_BRUSH_TIME_LEFT: EntityKey.MAIN_BRUSH_TIME_LEFT_SENSOR,
        Property.SIDE_BRUSH_TIME_LEFT: EntityKey.SIDE_BRUSH_TIME_LEFT_SENSOR,
        Property.FILTER_TIME_LEFT: EntityKey.FILTER_TIME_LEFT_SENSOR,
        Property.MOP_TIME_LEFT: EntityKey.MOP_TIME_LEFT_SENSOR,
        Property.DRYING_TIME_LEFT: EntityKey.DRYING_TIME_LEFT_SENSOR,
        Property.TOTAL_CLEAN_TIME: EntityKey.TOTAL_CLEAN_TIME_SENSOR,
        Property.TOTAL_CLEAN_COUNT: EntityKey.TOTAL_CLEAN_COUNT_SENSOR,
        Property.TOTAL_CLEAN_AREA: EntityKey.TOTAL_CLEAN_AREA_SENSOR,
        Property.CHILD_LOCK: EntityKey.CHILD_LOCK_SWITCH,
        Property.CARPET_BOOST: EntityKey.CARPET_BOOST_SWITCH,
        Property.RESUME_AFTER_CHARGE: EntityKey.RESUME_AFTER_CHARGE_SWITCH,
        Property.DO_NOT_DISTURB: EntityKey.DO_NOT_DISTURB_SWITCH,
        Property.VOLUME: EntityKey.VOLUME_NUMBER,
        Property.MOP_WASH: EntityKey.MOP_WASH_SWITCH,
        Property.MOP_WASH_FREQUENCY: EntityKey.MOP_WASH_FREQUENCY_SELECT,
        Property.MOP_WASH_AREA_INTERVAL: EntityKey.MOP_WASH_AREA_INTERVAL_SELECT,
        Property.MOP_WASH_TIME_INTERVAL: EntityKey.MOP_WASH_TIME_INTERVAL_NUMBER,
        Property.MOP_DRYING_TIME: EntityKey.MOP_DRYING_TIME_SELECT,
        Property.AUTO_DUST_COLLECTION: EntityKey.AUTO_DUST_COLLECTION_SWITCH,
        Property.AUTO_MOP_DRYING: EntityKey.AUTO_MOP_DRYING_SWITCH,
        Property.MOP_WASH_WATER_MODE: EntityKey.MOP_WASH_WATER_MODE_SELECT,
        Property.MOP_WASH_TEMPERATURE: EntityKey.MOP_WASH_TEMPERATURE_SELECT,
        Property.DUST_COLLECTION_FREQUENCY: EntityKey.DUST_COLLECTION_FREQUENCY_SELECT,
        Property.CARPET_CLEANING_METHOD: EntityKey.CARPET_CLEANING_METHOD_SELECT,
    }
)

#: Button entities backed by one optional :class:`ModelActions` field, created
#: only when the model defines that action. A spec template can list an action
#: the retail hardware cannot perform (the S40 Pro dock actions); such actions
#: stay ``None`` so they create no button.
ACTION_ENTITIES: Mapping[str, EntityKey] = MappingProxyType(
    {
        "start_dust_arrest": EntityKey.DUST_ARREST_BUTTON,
        "start_mop_wash": EntityKey.START_MOP_WASH_BUTTON,
        "stop_mop_wash": EntityKey.STOP_MOP_WASH_BUTTON,
        "start_dry": EntityKey.START_DRY_BUTTON,
        "stop_dry": EntityKey.STOP_DRY_BUTTON,
        "reset_main_brush": EntityKey.RESET_MAIN_BRUSH_BUTTON,
        "reset_side_brush": EntityKey.RESET_SIDE_BRUSH_BUTTON,
        "reset_filter": EntityKey.RESET_FILTER_BUTTON,
        "reset_mop": EntityKey.RESET_MOP_BUTTON,
    }
)
