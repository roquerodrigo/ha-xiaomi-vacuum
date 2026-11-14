"""Tests for the per-model MIoT spec registry."""

from __future__ import annotations

import pytest
from homeassistant.components.vacuum.const import VacuumActivity

from custom_components.xiaomi_vacuum.spec import (
    B108GL,
    C102GL,
    D109GL,
    DEFAULT_MODEL,
    MODELS,
    OV71GL,
    STATUS_MEANINGS,
    SUPPORTED_MODELS,
    ConfigThenCustomSweep,
    DirectRoomSweep,
    Property,
    get_spec,
)


def test_registry_lists_all_supported_models():
    assert set(SUPPORTED_MODELS) == {
        "xiaomi.vacuum.d109gl",
        "xiaomi.vacuum.b108gl",
        "xiaomi.vacuum.ov71gl",
        "xiaomi.vacuum.c102gl",
    }
    assert set(MODELS) == set(SUPPORTED_MODELS)
    assert DEFAULT_MODEL == "xiaomi.vacuum.d109gl"


def test_get_spec_returns_known_model(model):
    assert get_spec(model) is MODELS[model]
    assert get_spec(model).model == model


def test_get_spec_unknown_model_falls_back_with_warning(caplog):
    spec = get_spec("xiaomi.vacuum.zzzzz")
    assert spec is D109GL
    assert any("Unknown vacuum model" in r.message for r in caplog.records)


def test_get_spec_none_model_falls_back():
    assert get_spec(None) is D109GL


def test_d109_status_activity_values_are_all_vacuum_activities():
    assert all(
        isinstance(v, VacuumActivity) for v in D109GL.status_to_activity.values()
    )


def test_b108_has_no_dock_only_entities():
    from custom_components.xiaomi_vacuum.spec import EntityKey

    assert EntityKey.DUST_ARREST_BUTTON not in B108GL.entities
    assert EntityKey.SWEEP_ROUTE_SELECT not in B108GL.entities
    assert EntityKey.OBSTACLE_AVOIDANCE_SELECT not in B108GL.entities
    # The dock-only actions must be None on the S20+.
    assert B108GL.actions.start_dust_arrest is None
    assert B108GL.actions.start_mop_wash is None


def test_d109_has_dock_only_entities():
    from custom_components.xiaomi_vacuum.spec import EntityKey

    assert EntityKey.DUST_ARREST_BUTTON in D109GL.entities
    assert EntityKey.SWEEP_ROUTE_SELECT in D109GL.entities
    assert EntityKey.OBSTACLE_AVOIDANCE_SELECT in D109GL.entities


def test_mop_water_levels_include_off_on_both_models():
    assert B108GL.mop_water_levels["off"] == 0
    assert D109GL.mop_water_levels["off"] == 0


def test_b108_return_home_and_continue_use_different_services():
    """S20+ return-home hits the battery service; continue hits vacuum-extend."""
    assert B108GL.actions.return_home == {"siid": 3, "aiid": 1}
    assert B108GL.actions.continue_sweep == {"siid": 6, "aiid": 1}
    # d109gl keeps both inside the vacuum service (SIID 2).
    assert D109GL.actions.return_home["siid"] == 2
    assert D109GL.actions.continue_sweep["siid"] == 2


def test_room_cleaning_flows_carry_their_actions():
    """d109gl uses the direct start-vacuum-room-sweep; b108gl configures+starts."""
    assert D109GL.room_cleaning == DirectRoomSweep(
        {"siid": 2, "aiid": 16, "in_piid": 15}
    )
    # Captured from the Mi Home app — the spec's aiid 13 is ignored by the robot.
    assert B108GL.room_cleaning == ConfigThenCustomSweep(
        set_room_clean_configs={"siid": 2, "aiid": 10},
        start_custom_sweep={"siid": 6, "aiid": 7},
    )
    assert B108GL.room_cleaning.actions == (
        {"siid": 2, "aiid": 10},
        {"siid": 6, "aiid": 7},
    )


def test_b108_send_commands_exclude_mop_wash_and_dry():
    for cmd in ("start_mop_wash", "stop_mop_wash", "start_dry", "stop_dry"):
        assert cmd not in B108GL.send_commands
        assert cmd in D109GL.send_commands


def test_spec_reverse_name_maps():
    assert D109GL.fan_speed_names[2] == "basic"
    assert B108GL.mop_water_level_names[0] == "off"
    assert D109GL.clean_times_names[3] == "three_times"


def test_d109_entities_include_the_optional_selects_and_button():
    from custom_components.xiaomi_vacuum.spec import EntityKey

    entities = D109GL.entities
    assert EntityKey.VACUUM in entities
    assert EntityKey.STATUS_SENSOR in entities
    assert EntityKey.SWEEP_ROUTE_SELECT in entities
    assert EntityKey.OBSTACLE_AVOIDANCE_SELECT in entities
    assert EntityKey.DUST_ARREST_BUTTON in entities


def test_b108_entities_exclude_the_optional_selects_and_button():
    from custom_components.xiaomi_vacuum.spec import EntityKey

    entities = B108GL.entities
    assert EntityKey.VACUUM in entities  # base set still present
    assert EntityKey.SWEEP_ROUTE_SELECT not in entities
    assert EntityKey.OBSTACLE_AVOIDANCE_SELECT not in entities
    assert EntityKey.DUST_ARREST_BUTTON not in entities


def test_status_views_follow_the_catalog():
    for code, slug in D109GL.status.items():
        meaning = STATUS_MEANINGS[slug]
        assert D109GL.status_to_activity[code] is meaning.activity
        assert D109GL.status_slugs[code] == slug
        assert (code in D109GL.idle_statuses) == meaning.is_idle
        assert D109GL.cleaning_job_signals[code] is meaning.cleaning_job


def test_every_catalog_slug_is_used_by_a_model():
    used = {slug for spec in MODELS.values() for slug in spec.status.values()}
    assert used == set(STATUS_MEANINGS)


@pytest.mark.parametrize(
    ("code", "activity"),
    [
        (7, VacuumActivity.DOCKED),
        (19, VacuumActivity.RETURNING),
        (20, VacuumActivity.RETURNING),
    ],
)
def test_d109_activities_follow_the_mi_home_status_strings(code, activity):
    """7 washes the mop at the dock; 19 and 20 drive back to it mid-job."""
    assert D109GL.status_to_activity[code] is activity


def test_cleaning_job_signals_are_decisive_for_unambiguous_statuses():
    from custom_components.xiaomi_vacuum.spec import CleaningJobSignal

    for meaning in STATUS_MEANINGS.values():
        if meaning.is_idle:
            assert meaning.cleaning_job is CleaningJobSignal.FINISHED
        if meaning.activity in (VacuumActivity.CLEANING, VacuumActivity.PAUSED):
            assert meaning.cleaning_job is CleaningJobSignal.IN_PROGRESS


def test_d109_route_and_obstacle_enumerations_are_per_model():
    """X20 Max carries its sweep-route / obstacle-avoidance tables on the spec."""
    assert D109GL.sweep_routes == {"quick": 1, "daily": 2, "careful": 3}
    assert D109GL.obstacle_avoidances == {
        "less_collisions": 0,
        "high_coverage": 1,
    }
    # S20+ exposes neither property, so neither table is populated.
    assert B108GL.sweep_routes == {}
    assert B108GL.obstacle_avoidances == {}


def test_spec_fields_are_immutable():
    """``frozen=True`` is backed by ``MappingProxyType`` on every dict field.

    Driven off ``MAPPING_FIELDS`` itself, so a field added to the dataclass
    without a read-only wrapper fails here instead of silently sharing state.
    """
    from custom_components.xiaomi_vacuum.spec import MAPPING_FIELDS, Property

    # Keys the X20 Max actually populates, so the assignment reaches the
    # mapping instead of short-circuiting on a missing key.
    mutations: dict[str, tuple[object, object]] = {
        "property_mapping": (Property.STATUS, {"siid": 0, "piid": 0}),
        "status": (1, "idle"),
        "fan_speeds": ("silent", 99),
        "sweep_mop_types": ("sweep", 99),
        "clean_times": ("one_time", 99),
        "mop_water_levels": ("level_1", 99),
        "charging_state_slugs": (1, "boom"),
        "sweep_routes": ("quick", 99),
        "obstacle_avoidances": ("less_collisions", 99),
        "mop_wash_frequencies": ("by_room", 99),
        "mop_wash_area_intervals": ("five_square_meters", 99),
        "mop_drying_times": ("2_hours", 99),
    }
    assert set(mutations) == set(MAPPING_FIELDS)
    for field_name, (key, value) in mutations.items():
        mapping = getattr(D109GL, field_name)
        with pytest.raises(TypeError):
            mapping[key] = value  # type: ignore[index]


@pytest.mark.parametrize(
    ("spec", "activity", "expected_code"),
    [
        # Status code 4 ("sweeping") is the canonical CLEANING representative on
        # both models — listed before the other CLEANING entries (``remote``,
        # ``building_map``) in the table, so it wins the first-match lookup.
        (D109GL, VacuumActivity.CLEANING, 4),
        (B108GL, VacuumActivity.CLEANING, 4),
        (D109GL, VacuumActivity.PAUSED, 5),
        (B108GL, VacuumActivity.PAUSED, 5),
        (D109GL, VacuumActivity.IDLE, 1),
        (B108GL, VacuumActivity.IDLE, 1),
        (D109GL, VacuumActivity.RETURNING, 6),
        (B108GL, VacuumActivity.RETURNING, 6),
    ],
)
def test_status_code_for_returns_canonical_code(spec, activity, expected_code):
    assert spec.status_code_for(activity) == expected_code
    # Round-trip: the returned code maps back to the requested activity.
    assert spec.status_to_activity[expected_code] is activity


def test_status_code_for_unknown_activity_raises():
    with pytest.raises(ValueError, match="No status code maps to activity"):
        # ERROR is intentionally not in the status table (driven by faults), so
        # no canonical code exists for it.
        D109GL.status_code_for(VacuumActivity.ERROR)


def test_every_action_entity_and_send_command_names_a_model_action():
    from dataclasses import fields

    from custom_components.xiaomi_vacuum.spec import ModelActions
    from custom_components.xiaomi_vacuum.spec.entity_requirements import (
        ACTION_ENTITIES,
    )
    from custom_components.xiaomi_vacuum.spec.send_commands import (
        SEND_COMMAND_ACTIONS,
    )

    action_names = {field.name for field in fields(ModelActions)}
    assert set(ACTION_ENTITIES) <= action_names
    assert set(SEND_COMMAND_ACTIONS) <= action_names


def test_send_commands_follow_the_defined_actions():
    from dataclasses import replace

    spec = replace(D109GL, actions=replace(D109GL.actions, stop_dry=None))
    assert "stop_dry" not in spec.send_commands
    assert spec.send_commands["start_dry"] == D109GL.actions.start_dry


def test_custom_cleanings_wired_only_where_verified():
    assert D109GL.actions.start_user_define_sweep == {
        "siid": 2,
        "aiid": 42,
        "in_piid": 43,
    }
    assert D109GL.property_mapping[Property.USER_DEFINE_SWEEP_CONFIG] == {
        "siid": 2,
        "piid": 42,
        "polled": False,
    }
    assert Property.USER_DEFINE_SWEEP_CONFIG not in D109GL.polled_properties
    for spec in (B108GL, OV71GL, C102GL):
        assert spec.actions.start_user_define_sweep is None
        assert Property.USER_DEFINE_SWEEP_CONFIG not in spec.property_mapping


@pytest.mark.parametrize("spec", [D109GL, B108GL, OV71GL], ids=lambda s: s.model)
def test_in_house_models_keep_their_property_backed_entities(spec):
    """Gating these on mapped properties must not drop them from older models."""
    from custom_components.xiaomi_vacuum.spec import EntityKey

    for key in (
        EntityKey.MAP_IMAGE,
        EntityKey.MOP_PAD_SENSOR,
        EntityKey.SWEEP_MOP_TYPE_SELECT,
        EntityKey.CLEAN_TIMES_SELECT,
        EntityKey.MOP_WATER_LEVEL_SELECT,
    ):
        assert key in spec.entities


@pytest.mark.parametrize(
    ("spec", "supported"),
    [(D109GL, True), (B108GL, True), (OV71GL, True), (C102GL, True)],
    ids=lambda v: getattr(v, "model", str(v)),
)
def test_supports_room_clean(spec, supported):
    assert spec.supports_room_clean is supported


def test_a_model_without_a_room_cleaning_flow_does_not_support_room_clean():
    from dataclasses import replace

    assert replace(C102GL, room_cleaning=None).supports_room_clean is False


def test_task_status_decides_the_cleaning_job_when_mapped():
    from custom_components.xiaomi_vacuum.spec import CleaningJobSignal

    # Charging (6) and washing (9) happen mid-job and after it.
    assert C102GL.cleaning_job_signal(6, 1) is CleaningJobSignal.IN_PROGRESS
    assert C102GL.cleaning_job_signal(9, 0) is CleaningJobSignal.FINISHED
    # Not polled yet: fall back to the status table.
    assert C102GL.cleaning_job_signal(9, None) is CleaningJobSignal.INCONCLUSIVE
    assert C102GL.cleaning_job_signal(1, None) is CleaningJobSignal.IN_PROGRESS
    assert C102GL.cleaning_job_signal(None, None) is CleaningJobSignal.INCONCLUSIVE
    assert C102GL.cleaning_job_signal(999, None) is CleaningJobSignal.INCONCLUSIVE


def test_task_status_is_ignored_by_models_that_do_not_map_it():
    from custom_components.xiaomi_vacuum.spec import CleaningJobSignal

    assert D109GL.cleaning_job_signal(2, 1) is CleaningJobSignal.FINISHED
    assert D109GL.is_idle(2, 1) is True


def test_open_task_vetoes_a_fresh_start_from_an_idle_status():
    assert C102GL.is_idle(6, 1) is False  # recharging mid-job: resume instead
    assert C102GL.is_idle(6, 0) is True
    assert C102GL.is_idle(13, None) is True
    assert C102GL.is_idle(1, 0) is False  # sweeping is never idle


def test_status_code_for_prefers_the_canonical_slug_whatever_the_order():
    from dataclasses import replace

    from custom_components.xiaomi_vacuum.spec import StatusSlug

    spec = replace(
        D109GL, status={16: StatusSlug.SWEEPING_AND_MOPPING, 4: StatusSlug.SWEEPING}
    )
    assert spec.status_code_for(VacuumActivity.CLEANING) == 4


def test_status_code_for_falls_back_to_the_first_matching_code():
    from dataclasses import replace

    from custom_components.xiaomi_vacuum.spec import StatusSlug

    spec = replace(D109GL, status={17: StatusSlug.MOPPING, 16: StatusSlug.REMOTE})
    assert spec.status_code_for(VacuumActivity.CLEANING) == 17
    with pytest.raises(ValueError, match="No status code"):
        spec.status_code_for(VacuumActivity.PAUSED)


def test_plain_fault_reading_reports_nothing_without_the_property():
    assert B108GL.live_fault_code({}) is None
    assert B108GL.live_fault_code({"fault": 7}) == 7


def test_consumable_and_battery_entities_need_their_property():
    from dataclasses import replace

    from custom_components.xiaomi_vacuum.spec import EntityKey

    spec = replace(
        D109GL,
        property_mapping={
            name: binding
            for name, binding in D109GL.property_mapping.items()
            if name not in (Property.SIDE_BRUSH_LIFE, Property.BATTERY_LEVEL)
        },
    )
    assert EntityKey.SIDE_BRUSH_LIFE_SENSOR not in spec.entities
    assert EntityKey.BATTERY_SENSOR not in spec.entities
    assert EntityKey.MAIN_BRUSH_LIFE_SENSOR in spec.entities


def test_shared_catalogs_are_read_only():
    from custom_components.xiaomi_vacuum.spec import (
        CANONICAL_STATUSES,
        StatusSlug,
    )
    from custom_components.xiaomi_vacuum.spec.entity_requirements import (
        ACTION_ENTITIES,
        PROPERTY_ENTITIES,
    )
    from custom_components.xiaomi_vacuum.spec.enumerations import FAN_SPEEDS

    for catalog in (
        STATUS_MEANINGS,
        CANONICAL_STATUSES,
        PROPERTY_ENTITIES,
        ACTION_ENTITIES,
        FAN_SPEEDS,
    ):
        with pytest.raises(TypeError):
            catalog[StatusSlug.IDLE] = None  # type: ignore[index]
