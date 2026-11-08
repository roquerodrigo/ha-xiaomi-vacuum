"""Invariants every registered model must hold, run once per model."""

from __future__ import annotations

import pytest
from homeassistant.components.vacuum.const import VacuumActivity
from homeassistant.helpers import entity_registry as er

from custom_components.xiaomi_vacuum.binary_sensor import _BINARY_SENSOR_CLASSES
from custom_components.xiaomi_vacuum.button import _BUTTON_CLASSES
from custom_components.xiaomi_vacuum.const import DOMAIN
from custom_components.xiaomi_vacuum.image import _IMAGE_CLASSES
from custom_components.xiaomi_vacuum.number import _NUMBER_CLASSES
from custom_components.xiaomi_vacuum.select import _SELECT_CLASSES
from custom_components.xiaomi_vacuum.sensor import _SENSOR_CLASSES
from custom_components.xiaomi_vacuum.spec import MODELS, EntityKey, Property
from custom_components.xiaomi_vacuum.switch import _SWITCH_CLASSES
from custom_components.xiaomi_vacuum.vacuum import _VACUUM_CLASSES

from .conftest import MODEL_FIXTURES

_PLATFORM_CLASSES = {
    **_BINARY_SENSOR_CLASSES,
    **_BUTTON_CLASSES,
    **_IMAGE_CLASSES,
    **_NUMBER_CLASSES,
    **_SELECT_CLASSES,
    **_SENSOR_CLASSES,
    **_SWITCH_CLASSES,
    **_VACUUM_CLASSES,
}

#: Each value-table field and the property whose values it names.
_VALUE_TABLES = {
    Property.FAN_SPEED: "fan_speeds",
    Property.SWEEP_MOP_TYPE: "sweep_mop_types",
    Property.CLEAN_TIMES: "clean_times",
    Property.MOP_WATER_LEVEL: "mop_water_levels",
    Property.SWEEP_ROUTE: "sweep_routes",
    Property.OBSTACLE_AVOIDANCE_STRATEGY: "obstacle_avoidances",
    Property.CHARGING_STATE: "charging_state_slugs",
}

#: Activities the vacuum entity patches optimistically after a command.
_PATCHED_ACTIVITIES = (
    VacuumActivity.CLEANING,
    VacuumActivity.PAUSED,
    VacuumActivity.IDLE,
    VacuumActivity.RETURNING,
)

_SPECS = pytest.mark.parametrize("spec", list(MODELS.values()), ids=list(MODELS))


def test_every_model_has_a_test_fixture():
    assert set(MODEL_FIXTURES) == set(MODELS)


def test_every_entity_key_has_an_entity_class():
    assert set(EntityKey) == set(_PLATFORM_CLASSES)


@_SPECS
def test_status_and_fault_are_mapped(spec):
    assert Property.STATUS in spec.property_mapping
    assert {Property.FAULT, Property.FAULT_IDS} & set(spec.property_mapping)


@_SPECS
def test_no_two_properties_share_an_address(spec):
    addresses = [(b["siid"], b["piid"]) for b in spec.property_mapping.values()]
    assert len(addresses) == len(set(addresses))


@_SPECS
@pytest.mark.parametrize("activity", _PATCHED_ACTIVITIES)
def test_every_patched_activity_has_a_status_code(spec, activity):
    code = spec.status_code_for(activity)
    assert spec.status_to_activity[code] is activity


@_SPECS
@pytest.mark.parametrize(("name", "table"), list(_VALUE_TABLES.items()))
def test_value_tables_exist_exactly_for_mapped_properties(spec, name, table):
    assert bool(getattr(spec, table)) == (name in spec.property_mapping)


@_SPECS
def test_masks_are_contiguous_bit_ranges(spec):
    for mask in spec.property_masks.values():
        shifted = mask >> ((mask & -mask).bit_length() - 1)
        assert mask > 0
        assert shifted & (shifted + 1) == 0


@_SPECS
def test_room_cleaning_and_map_rooms_agree(spec):
    """A model listing its rooms from the property has to publish it."""
    if spec.room_cleaning is not None and not spec.map_format.carries_rooms:
        assert Property.ROOM_INFORMATION in spec.property_mapping


@_SPECS
def test_custom_cleanings_have_both_their_action_and_their_list(spec):
    """The service starts the action; its options are read from the property."""
    has_action = spec.actions.start_user_define_sweep is not None
    assert has_action == (Property.USER_DEFINE_SWEEP_CONFIG in spec.property_mapping)


@_SPECS
def test_a_mapped_charging_state_names_the_charging_slug(spec):
    """The battery and charging entities look for the ``charging`` slug."""
    if Property.CHARGING_STATE in spec.property_mapping:
        assert "charging" in spec.charging_state_slugs.values()


def test_the_sample_state_covers_every_polled_property(model):
    state = MODEL_FIXTURES[model]["state"]
    assert set(MODELS[model].polled_properties) <= set(state)


async def test_setup_creates_every_entity_the_spec_lists(
    hass, model, setup_integration_of_model
):
    spec = MODELS[model]
    registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(
        registry, setup_integration_of_model.entry_id
    )
    # The map image needs a cloud session, which the plain fixture has none of.
    expected = spec.entities - {EntityKey.MAP_IMAGE}
    assert len(entries) == len(expected)
    for entry in entries:
        assert entry.platform == DOMAIN
        state = hass.states.get(entry.entity_id)
        assert state is not None
        assert state.state != "unavailable", entry.entity_id
