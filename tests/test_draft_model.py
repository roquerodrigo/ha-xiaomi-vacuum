"""Tests for the miot-spec draft generator in ``scripts/draft_model.py``."""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import fields
from pathlib import Path

import pytest

from custom_components.xiaomi_vacuum.spec import (
    C102GL,
    D109GL,
    ModelActions,
    Property,
    StatusSlug,
)

_ROOT = Path(__file__).parent.parent
_FIXTURES = Path(__file__).parent / "fixtures" / "miot_spec"


@pytest.fixture(scope="module")
def draft_model():
    spec = importlib.util.spec_from_file_location(
        "draft_model", _ROOT / "scripts" / "draft_model.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["draft_model"] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop("draft_model", None)


def _instance(name):
    return json.loads((_FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def _hand_written_actions(spec):
    return {
        field.name: (action["siid"], action["aiid"])
        for field in fields(ModelActions)
        if (action := getattr(spec.actions, field.name)) is not None
    }


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("Go Charging", "go_charging"),
        ("BreakCharging", "break_charging"),
        ("Level1", "level_1"),
        ("Full Speed", "full_speed"),
    ],
)
def test_slug_snake_cases_descriptions(draft_model, description, expected):
    assert draft_model.slug(description) == expected


def test_x20_max_draft_holds_every_hand_written_address(draft_model):
    result = draft_model.draft(_instance("xiaomi-d109gl"))
    for name, binding in D109GL.property_mapping.items():
        assert result.properties[name] == (binding["siid"], binding["piid"]), name
    for name, address in _hand_written_actions(D109GL).items():
        assert result.actions[name][:2] == address, name
    room_sweep = D109GL.room_cleaning.action
    assert result.room_sweep == (
        room_sweep["siid"],
        room_sweep["aiid"],
        room_sweep["in_piid"],
    )
    assert result.status == dict(D109GL.status)
    for table, values in result.value_tables.items():
        assert values == dict(getattr(D109GL, table)), table
    # The latching Device Fault is dropped next to the live Fault Ids list.
    assert "fault" not in result.properties
    # The published spec has more than the hand-written one wires: the hours left
    # on each consumable and their reset actions.
    assert set(result.properties) - set(D109GL.property_mapping) == {
        "mop_time_left",
        "main_brush_time_left",
        "side_brush_time_left",
        "filter_time_left",
    }
    assert set(result.actions) - set(_hand_written_actions(D109GL)) == {
        "reset_mop",
        "reset_main_brush",
        "reset_side_brush",
        "reset_filter",
    }


def test_x20_plus_draft_adopts_the_dreame_layout(draft_model):
    result = draft_model.draft(_instance("xiaomi-c102gl"))
    actions = _hand_written_actions(C102GL)
    for name in ("start_sweep", "stop_sweeping", "pause_sweeping", "continue_sweep"):
        assert result.actions[name][:2] == actions[name], name
    segment_clean = C102GL.room_cleaning.action
    assert result.dreame_start_clean == (
        segment_clean["siid"],
        segment_clean["aiid"],
        segment_clean["data_piid"],
    )
    assert result.status == dict(C102GL.status)
    assert result.value_tables["mop_water_levels"] == dict(C102GL.mop_water_levels)
    assert any("Dreame-built layout" in todo for todo in result.todos)
    assert result.booleans == {"do_not_disturb"}
    assert '"boolean": True' in draft_model.render("xiaomi.vacuum.x", result)


@pytest.mark.parametrize("name", ["xiaomi-d109gl", "xiaomi-c102gl"])
def test_rendered_draft_is_valid_python(draft_model, name):
    result = draft_model.draft(_instance(name))
    source = draft_model.render("xiaomi.vacuum.x", result)
    compile(source, "draft.py", "exec")
    assert "X = ModelSpec(" in source


def test_unknown_status_descriptions_are_left_as_todos(draft_model):
    instance = _instance("xiaomi-d109gl")
    status = next(
        prop
        for service in instance["services"]
        for prop in service.get("properties", [])
        if prop["type"].split(":")[3] == "status"
    )
    status["value-list"].append({"value": 99, "description": "Teleporting"})
    result = draft_model.draft(instance)
    assert result.status[99] == "Teleporting"
    assert result.status[1] is StatusSlug.IDLE
    assert "# TODO: 99 'Teleporting' has no StatusSlug" in draft_model.render(
        "xiaomi.vacuum.x", result
    )


def _service(instance, service_type):
    return next(
        service
        for service in instance["services"]
        if service["type"].split(":")[3] == service_type
    )


def test_a_missing_required_action_is_left_as_a_todo(draft_model):
    instance = _instance("xiaomi-d109gl")
    identify = _service(instance, "identify")
    identify["actions"] = []
    result = draft_model.draft(instance)
    assert "identify" not in result.actions
    assert any("required action identify" in todo for todo in result.todos)


def test_a_room_sweep_without_input_is_not_wired(draft_model):
    instance = _instance("xiaomi-d109gl")
    for action in _service(instance, "vacuum")["actions"]:
        if action["type"].split(":")[3] == "start-vacuum-room-sweep":
            action["in"] = []
    result = draft_model.draft(instance)
    assert any("takes no input" in todo for todo in result.todos)
    assert "room_cleaning=" not in draft_model.render("xiaomi.vacuum.x", result)


def test_charging_states_without_charging_are_left_as_a_todo(draft_model):
    instance = _instance("xiaomi-d109gl")
    for prop in _service(instance, "battery")["properties"]:
        if prop["type"].split(":")[3] == "charging-state":
            prop["value-list"] = [
                {"value": 1, "description": "Is Charging"},
                {"value": 2, "description": "Not Charging"},
            ]
    result = draft_model.draft(instance)
    assert any("no charging state is 'charging'" in todo for todo in result.todos)


#: Properties and actions the draft deliberately never maps, with the reason. A
#: new one belongs in the generator's tables unless the spec cannot locate it.
_NOT_DRAFTED: frozenset[str] = frozenset()


def test_the_generator_knows_every_property(draft_model):
    drafted = {
        *draft_model._PROPERTIES.values(),
        *draft_model._BRUSH_PROPERTIES.values(),
    }
    missing = {name.value for name in Property if name not in drafted}
    assert missing <= _NOT_DRAFTED, (
        f"teach scripts/draft_model.py where {sorted(missing)} live "
        "(_PROPERTIES), or list them in _NOT_DRAFTED with the reason"
    )


def test_the_generator_knows_every_action(draft_model):
    drafted = {*draft_model._ACTIONS.values(), *draft_model._BRUSH_ACTIONS.values()}
    missing = {field.name for field in fields(ModelActions)} - drafted
    assert missing <= _NOT_DRAFTED, (
        f"teach scripts/draft_model.py where {sorted(missing)} live "
        "(_ACTIONS), or list them in _NOT_DRAFTED with the reason"
    )
