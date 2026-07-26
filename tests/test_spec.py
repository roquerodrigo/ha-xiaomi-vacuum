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
    assert not _B108GL.has_dust_arrest
    assert not _B108GL.has_sweep_route
    assert not _B108GL.has_obstacle_avoidance
    assert not _B108GL.has_mop_wash_dry
    # The dock-only actions must be None on the S20+.
    assert _B108GL.actions.start_dust_arrest is None
    assert _B108GL.actions.start_mop_wash is None


def test_d109_has_dock_only_capabilities():
    assert _D109GL.has_dust_arrest
    assert _D109GL.has_sweep_route
    assert _D109GL.has_obstacle_avoidance
    assert _D109GL.has_mop_wash_dry


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
    assert Capability.MOP_WASH_DRY in caps


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


def test_has_capability_shortcuts_are_derived():
    assert _D109GL.has_dust_arrest is True
    assert _D109GL.has_sweep_route is True
    assert _D109GL.has_obstacle_avoidance is True
    assert _D109GL.has_mop_wash_dry is True
    assert _B108GL.has_dust_arrest is False
    assert _B108GL.has_sweep_route is False
    assert _B108GL.has_obstacle_avoidance is False
    assert _B108GL.has_mop_wash_dry is False
