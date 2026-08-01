"""Tests for the per-model MIoT spec registry."""

from __future__ import annotations

import pytest
from homeassistant.components.vacuum.const import VacuumActivity

from custom_components.xiaomi_vacuum.spec import (
    _B108GL,
    _D109GL,
    DEFAULT_MODEL,
    MODELS,
    SUPPORTED_MODELS,
    get_spec,
)


def test_registry_lists_both_supported_models():
    assert set(SUPPORTED_MODELS) == {"xiaomi.vacuum.d109gl", "xiaomi.vacuum.b108gl"}
    assert set(MODELS) == set(SUPPORTED_MODELS)
    assert DEFAULT_MODEL == "xiaomi.vacuum.d109gl"


@pytest.mark.parametrize(
    ("model", "spec"),
    [
        ("xiaomi.vacuum.d109gl", _D109GL),
        ("xiaomi.vacuum.b108gl", _B108GL),
    ],
)
def test_get_spec_returns_known_model(model, spec):
    assert get_spec(model) is spec


def test_get_spec_unknown_model_falls_back_with_warning(caplog):
    spec = get_spec("xiaomi.vacuum.zzzzz")
    assert spec is _D109GL
    assert any("Unknown vacuum model" in r.message for r in caplog.records)


def test_get_spec_none_model_falls_back():
    assert get_spec(None) is _D109GL


def test_d109_status_activity_values_are_all_vacuum_activities():
    assert all(
        isinstance(v, VacuumActivity) for v in _D109GL.status_to_activity.values()
    )


def test_b108_has_no_dock_only_capabilities():
    from custom_components.xiaomi_vacuum.spec import Capability

    caps = _B108GL.capabilities
    assert Capability.DUST_ARREST not in caps
    assert Capability.SWEEP_ROUTE not in caps
    assert Capability.OBSTACLE_AVOIDANCE not in caps
    # The dock-only actions must be None on the S20+.
    assert _B108GL.actions.start_dust_arrest is None
    assert _B108GL.actions.start_mop_wash is None


def test_d109_has_dock_only_capabilities():
    from custom_components.xiaomi_vacuum.spec import Capability

    caps = _D109GL.capabilities
    assert Capability.DUST_ARREST in caps
    assert Capability.SWEEP_ROUTE in caps
    assert Capability.OBSTACLE_AVOIDANCE in caps


def test_b108_mop_water_levels_include_off():
    assert _B108GL.mop_water_levels["off"] == 0
    assert "off" not in _D109GL.mop_water_levels


def test_b108_return_home_and_continue_use_different_services():
    """S20+ return-home hits the battery service; continue hits vacuum-extend."""
    assert _B108GL.actions.return_home == {"siid": 3, "aiid": 1}
    assert _B108GL.actions.continue_sweep == {"siid": 6, "aiid": 1}
    # d109gl keeps both inside the vacuum service (SIID 2).
    assert _D109GL.actions.return_home["siid"] == 2
    assert _D109GL.actions.continue_sweep["siid"] == 2


def test_room_clean_strategy_matches_action_set():
    """d109gl uses the direct start-vacuum-room-sweep; b108gl configures+starts."""
    # X20 Max: a single direct action carrying room ids as input.
    assert _D109GL.room_clean_strategy == "direct"
    assert _D109GL.actions.start_room_sweep == {"siid": 2, "aiid": 16, "in_piid": 15}
    assert _D109GL.actions.set_room_clean_configs is None
    assert _D109GL.actions.start_custom_sweep is None

    # S20+: no direct room-sweep action; two-step config + start-custom-sweep.
    # Captured from the Mi Home app — the spec's aiid 13 is ignored by the robot.
    assert _B108GL.room_clean_strategy == "config_then_custom"
    assert _B108GL.actions.start_room_sweep is None
    assert _B108GL.actions.set_room_clean_configs == {"siid": 2, "aiid": 10}
    assert _B108GL.actions.start_custom_sweep == {"siid": 6, "aiid": 7}


def test_b108_send_commands_exclude_mop_wash_and_dry():
    for cmd in ("start_mop_wash", "stop_mop_wash", "start_dry", "stop_dry"):
        assert cmd not in _B108GL.send_commands
        assert cmd in _D109GL.send_commands


def test_spec_reverse_name_maps():
    assert _D109GL.fan_speed_names[2] == "basic"
    assert _B108GL.mop_water_level_names[0] == "off"
    assert _D109GL.clean_times_names[3] == "three_times"


def test_d109_capabilities_include_all_optional():
    from custom_components.xiaomi_vacuum.spec import Capability

    caps = _D109GL.capabilities
    assert Capability.DUST_ARREST in caps
    assert Capability.SWEEP_ROUTE in caps
    assert Capability.OBSTACLE_AVOIDANCE in caps


def test_b108_capabilities_exclude_all_optional():

    assert _B108GL.capabilities == frozenset()


def test_d109_entities_include_capability_gated_selects_and_button():
    from custom_components.xiaomi_vacuum.spec import EntityKey

    entities = _D109GL.entities
    assert EntityKey.VACUUM in entities
    assert EntityKey.STATUS_SENSOR in entities
    assert EntityKey.SWEEP_ROUTE_SELECT in entities
    assert EntityKey.OBSTACLE_AVOIDANCE_SELECT in entities
    assert EntityKey.DUST_ARREST_BUTTON in entities


def test_b108_entities_exclude_capability_gated_selects_and_button():
    from custom_components.xiaomi_vacuum.spec import EntityKey

    entities = _B108GL.entities
    assert EntityKey.VACUUM in entities  # base set still present
    assert EntityKey.SWEEP_ROUTE_SELECT not in entities
    assert EntityKey.OBSTACLE_AVOIDANCE_SELECT not in entities
    assert EntityKey.DUST_ARREST_BUTTON not in entities


def test_status_back_compat_properties_match_status_table():
    # The legacy status_to_activity / status_slugs / idle_statuses views must
    # stay in sync with the new single `status` table.
    for code, status in _D109GL.status.items():
        assert _D109GL.status_to_activity[code] == status["activity"]
        assert _D109GL.status_slugs[code] == status["slug"]
        is_idle = code in _D109GL.idle_statuses
        assert is_idle == status["is_idle"]


def test_d109_route_and_obstacle_enumerations_are_per_model():
    """X20 Max carries its sweep-route / obstacle-avoidance tables on the spec."""
    assert _D109GL.sweep_routes == {"quick": 1, "daily": 2, "careful": 3}
    assert _D109GL.obstacle_avoidances == {
        "less_collisions": 0,
        "high_coverage": 1,
    }
    # S20+ exposes neither property, so neither table is populated.
    assert _B108GL.sweep_routes == {}
    assert _B108GL.obstacle_avoidances == {}


def test_spec_fields_are_immutable():
    """``frozen=True`` is backed by ``MappingProxyType`` on the dict fields."""
    from custom_components.xiaomi_vacuum.spec import Property

    with pytest.raises(TypeError):
        _D109GL.fan_speeds["silent"] = 99  # type: ignore[index]
    with pytest.raises(TypeError):
        _D109GL.property_mapping[Property.STATUS] = {"siid": 0, "piid": 0}  # type: ignore[index]
    # ``send_commands`` is wrapped too, so a stray mutation can't introduce a
    # whitelist entry that the integration would happily route to the device.
    with pytest.raises(TypeError):
        _D109GL.send_commands["boom"] = {"siid": 0, "aiid": 0}  # type: ignore[index]


@pytest.mark.parametrize(
    ("spec", "activity", "expected_code"),
    [
        # Status code 4 ("sweeping") is the canonical CLEANING representative on
        # both models — listed before the other CLEANING entries (``remote``,
        # ``building_map``) in the table, so it wins the first-match lookup.
        (_D109GL, VacuumActivity.CLEANING, 4),
        (_B108GL, VacuumActivity.CLEANING, 4),
        (_D109GL, VacuumActivity.PAUSED, 5),
        (_B108GL, VacuumActivity.PAUSED, 5),
        (_D109GL, VacuumActivity.IDLE, 1),
        (_B108GL, VacuumActivity.IDLE, 1),
        (_D109GL, VacuumActivity.RETURNING, 6),
        (_B108GL, VacuumActivity.RETURNING, 6),
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
        _D109GL.status_code_for(VacuumActivity.ERROR)


def test_require_action_returns_action_when_present():
    from custom_components.xiaomi_vacuum.spec import _require_action

    action = {"siid": 2, "aiid": 19}
    assert _require_action(action, "start_mop_wash") is action


def test_require_action_raises_at_import_time_when_absent():
    """A model referencing an action it does not define is caught now, not later.

    Previously a bare ``typing.cast`` silenced the type checker, so a None would
    be stored and fail with a ``TypeError`` only when the command was sent.
    """
    from custom_components.xiaomi_vacuum.spec import _require_action

    with pytest.raises(ValueError, match="needs an action this model defines"):
        _require_action(None, "start_mop_wash")
