#!/usr/bin/env python3
# ruff: noqa: T201
"""
Draft the spec module of a new vacuum model from its published miot-spec.

Run: uv run scripts/draft_model.py <model> [--version N] [--spec FILE]
  model:     the model string the handshake reports, e.g. xiaomi.vacuum.c108gl
  --version: the spec version to draft from (default: the highest released)
  --spec:    read the miot-spec instance from FILE instead of miot-spec.org

Prints a draft ``spec/<model>.py`` to stdout. Every property and action whose
service and URN type match one the integration already knows is mapped, and the
status and value tables come from the spec's value lists. What the draft cannot
decide is left as ``TODO`` comments: ambiguous services, status descriptions with
no ``StatusSlug``, the room-cleaning flow, and anything only the Mi Home app or a
real device can confirm (see ADDING_A_MODEL.md).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypedDict

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from custom_components.xiaomi_vacuum.spec import Property, StatusSlug  # noqa: E402

_INSTANCES_URL = "https://miot-spec.org/miot-spec-v2/instances?status=all"
_INSTANCE_URL = "https://miot-spec.org/miot-spec-v2/instance?type={urn}"
_TIMEOUT_SECONDS = 30


class ValueListEntry(TypedDict):
    """One allowed value of a miot-spec property."""

    value: int
    description: str


MiotSpecProperty = TypedDict(
    "MiotSpecProperty",
    {
        "iid": int,
        "type": str,
        "description": str,
        "format": str,
        "value-list": list[ValueListEntry],
    },
    total=False,
)


class MiotSpecAction(TypedDict, total=False):
    """One action of a miot-spec service."""

    iid: int
    type: str
    description: str
    # "in" is a keyword, so the input piids are read with .get("in").


class MiotSpecService(TypedDict, total=False):
    """One service of a miot-spec instance."""

    iid: int
    type: str
    description: str
    properties: list[MiotSpecProperty]
    actions: list[MiotSpecAction]


class MiotSpecInstance(TypedDict):
    """A miot-spec device instance."""

    type: str
    services: list[MiotSpecService]


#: (service type, property type) → the property it publishes on every model seen.
_PROPERTIES: dict[tuple[str, str], Property] = {
    ("vacuum", "status"): Property.STATUS,
    ("vacuum", "fault-ids"): Property.FAULT_IDS,
    ("vacuum", "fault"): Property.FAULT,
    ("vacuum", "sweep-mop-type"): Property.SWEEP_MOP_TYPE,
    ("vacuum", "cleaning-area"): Property.CLEANING_AREA,
    ("vacuum-extend", "cleaning-area"): Property.CLEANING_AREA,
    ("vacuum", "cleaning-time"): Property.CLEANING_TIME,
    ("vacuum-extend", "cleaning-time"): Property.CLEANING_TIME,
    ("vacuum", "clean-times"): Property.CLEAN_TIMES,
    ("vacuum", "mode"): Property.FAN_SPEED,
    ("vacuum", "suction-level"): Property.FAN_SPEED,
    ("vacuum", "mop-water-output-level"): Property.MOP_WATER_LEVEL,
    ("vacuum-extend", "mop-mode"): Property.MOP_WATER_LEVEL,
    ("vacuum", "mop-status"): Property.MOP_STATUS,
    ("vacuum-extend", "mop-status"): Property.MOP_STATUS,
    ("vacuum", "room-information"): Property.ROOM_INFORMATION,
    ("vacuum-extend", "room-info"): Property.ROOM_INFORMATION,
    ("vacuum", "last-clean-time"): Property.LAST_CLEAN_TIME,
    ("vacuum-map", "map-obj-name"): Property.MAP_OBJ_NAME,
    ("vacuum", "sweep-route"): Property.SWEEP_ROUTE,
    ("vacuum", "obstacle-avoidance-strategy"): Property.OBSTACLE_AVOIDANCE_STRATEGY,
    ("vacuum", "user-define-sweep-cfg"): Property.USER_DEFINE_SWEEP_CONFIG,
    ("vacuum", "dry-left-time"): Property.DRYING_TIME_LEFT,
    ("vacuum-extend", "task-status"): Property.TASK_STATUS,
    ("vacuum-extend", "break-point-restart"): Property.RESUME_AFTER_CHARGE,
    ("vacuum-extend", "carpet-press"): Property.CARPET_BOOST,
    ("vacuum-extend", "child-lock"): Property.CHILD_LOCK,
    ("do-not-disturb", "enable"): Property.DO_NOT_DISTURB,
    ("audio", "volume"): Property.VOLUME,
    ("alarm", "volume"): Property.VOLUME,
    ("vacuum", "carpet-boost"): Property.CARPET_BOOST,
    ("vacuum", "sweep-break-switch"): Property.RESUME_AFTER_CHARGE,
    ("physical-controls-locked", "physical-controls-locked"): Property.CHILD_LOCK,
    ("no-disturb", "no-disturb"): Property.DO_NOT_DISTURB,
    ("vacuum", "enable-mop-wash"): Property.MOP_WASH,
    ("vacuum", "frequency-mop-wash"): Property.MOP_WASH_FREQUENCY,
    ("vacuum", "frequency-mop-wash-no-tank"): Property.MOP_WASH_AREA_INTERVAL,
    ("vacuum", "frequency-mop-wash-by-time"): Property.MOP_WASH_TIME_INTERVAL,
    ("vacuum", "drying-time"): Property.MOP_DRYING_TIME,
    ("vacuum", "auto-dust-arrest"): Property.AUTO_DUST_COLLECTION,
    ("vacuum", "auto-mop-dry"): Property.AUTO_MOP_DRYING,
    ("vacuum", "water-output-for-washing-mop"): Property.MOP_WASH_WATER_MODE,
    ("vacuum", "wash-mop-water-temperature"): Property.MOP_WASH_TEMPERATURE,
    ("vacuum", "dust-arrest-frequency"): Property.DUST_COLLECTION_FREQUENCY,
    ("vacuum", "carpet-cleaning-method"): Property.CARPET_CLEANING_METHOD,
    ("battery", "battery-level"): Property.BATTERY_LEVEL,
    ("battery", "charging-state"): Property.CHARGING_STATE,
    ("mop", "mop-life-level"): Property.MOP_LIFE,
    ("mop", "mop-left-time"): Property.MOP_TIME_LEFT,
    ("filter", "filter-life-level"): Property.FILTER_LIFE,
    ("filter", "filter-left-time"): Property.FILTER_TIME_LEFT,
    ("clean-logs", "total-clean-time"): Property.TOTAL_CLEAN_TIME,
    ("clean-logs", "total-clean-times"): Property.TOTAL_CLEAN_COUNT,
    ("clean-logs", "total-clean-area"): Property.TOTAL_CLEAN_AREA,
}

#: Brush services publish the same types; the service description tells them apart.
_BRUSH_PROPERTIES: dict[tuple[str, str], Property] = {
    ("main", "brush-life-level"): Property.MAIN_BRUSH_LIFE,
    ("main", "brush-left-time"): Property.MAIN_BRUSH_TIME_LEFT,
    ("side", "brush-life-level"): Property.SIDE_BRUSH_LIFE,
    ("side", "brush-left-time"): Property.SIDE_BRUSH_TIME_LEFT,
}

#: (service type, action type) → the ``ModelActions`` field. When a spec has
#: several candidates for one field, the first one in the spec's order wins.
_ACTIONS: dict[tuple[str, str], str] = {
    ("vacuum", "start-sweep"): "start_sweep",
    ("vacuum", "stop-sweeping"): "stop_sweeping",
    ("vacuum", "stop-and-gocharge"): "return_home",
    ("battery", "start-charge"): "return_home",
    ("vacuum", "pause-sweeping"): "pause_sweeping",
    ("vacuum", "continue-sweep"): "continue_sweep",
    ("vacuum-extend", "continue-sweep"): "continue_sweep",
    ("identify", "identify"): "identify",
    ("vacuum-extend", "find-vacuum"): "identify",
    ("audio", "position"): "identify",
    ("vacuum", "start-only-sweep"): "start_only_sweep",
    ("vacuum", "start-mop"): "start_mop",
    ("vacuum", "start-sweep-mop"): "start_sweep_mop",
    ("vacuum", "start-zone-sweep"): "start_zone_sweep",
    ("vacuum", "start-user-define-sweep"): "start_user_define_sweep",
    ("vacuum", "start-dust-arrest"): "start_dust_arrest",
    ("vacuum", "start-mop-wash"): "start_mop_wash",
    ("vacuum", "stop-mop-wash"): "stop_mop_wash",
    ("vacuum", "start-dry"): "start_dry",
    ("vacuum", "stop-dry"): "stop_dry",
    ("filter", "reset-filter-life"): "reset_filter",
    ("mop", "reset-mop-life"): "reset_mop",
}

_BRUSH_ACTIONS: dict[str, str] = {
    "main": "reset_main_brush",
    "side": "reset_side_brush",
}

#: ``ModelActions`` fields without a default: the module does not load without them.
_REQUIRED_ACTIONS: tuple[str, ...] = (
    "start_sweep",
    "stop_sweeping",
    "return_home",
    "pause_sweeping",
    "continue_sweep",
    "identify",
)

#: The charging-state slug the battery and charging entities look for.
_CHARGING_SLUG = "charging"

#: Actions taking the input property named by their first ``in`` piid.
_INPUT_ACTIONS = frozenset({"start_zone_sweep", "start_user_define_sweep"})

#: Value tables drafted from a property's value list, by ``ModelSpec`` field.
_VALUE_TABLES: dict[Property, str] = {
    Property.FAN_SPEED: "fan_speeds",
    Property.SWEEP_MOP_TYPE: "sweep_mop_types",
    Property.CLEAN_TIMES: "clean_times",
    Property.MOP_WATER_LEVEL: "mop_water_levels",
    Property.SWEEP_ROUTE: "sweep_routes",
    Property.OBSTACLE_AVOIDANCE_STRATEGY: "obstacle_avoidances",
    Property.MOP_WASH_FREQUENCY: "mop_wash_frequencies",
    Property.MOP_WASH_AREA_INTERVAL: "mop_wash_area_intervals",
    Property.MOP_DRYING_TIME: "mop_drying_times",
    Property.MOP_WASH_WATER_MODE: "mop_wash_water_modes",
    Property.MOP_WASH_TEMPERATURE: "mop_wash_temperatures",
    Property.DUST_COLLECTION_FREQUENCY: "dust_collection_frequencies",
    Property.CARPET_CLEANING_METHOD: "carpet_cleaning_methods",
}

#: Where each value table's slugs are translated in ``translations/en.json``.
_TABLE_TRANSLATIONS: dict[str, tuple[str, ...]] = {
    "fan_speeds": ("vacuum", "xiaomi_vacuum", "state_attributes", "fan_speed"),
    "sweep_mop_types": ("select", "sweep_mop_type"),
    "clean_times": ("select", "clean_times"),
    "mop_water_levels": ("select", "mop_water_level"),
    "sweep_routes": ("select", "sweep_route"),
    "obstacle_avoidances": ("select", "obstacle_avoidance_strategy"),
    "mop_wash_frequencies": ("select", "mop_wash_frequency"),
    "mop_wash_area_intervals": ("select", "mop_wash_area_interval"),
    "mop_drying_times": ("select", "mop_drying_time"),
    "mop_wash_water_modes": ("select", "mop_wash_water_mode"),
    "mop_wash_temperatures": ("select", "mop_wash_temperature"),
    "dust_collection_frequencies": ("select", "dust_collection_frequency"),
    "carpet_cleaning_methods": ("select", "carpet_cleaning_method"),
}

#: Status descriptions other models publish for an existing slug.
_STATUS_SYNONYMS: dict[str, StatusSlug] = {
    "mapping": StatusSlug.BUILDING_MAP,
    "building": StatusSlug.BUILDING_MAP,
    "washing": StatusSlug.GO_WASH,
    "go_washing": StatusSlug.WASH_BREAK,
    "charging_completed": StatusSlug.CHARGED,
    "upgrading": StatusSlug.UPDATING,
    "washing_mop_pause": StatusSlug.WASHING_PAUSED,
    "remote_clean": StatusSlug.REMOTE,
}

#: Value descriptions other models publish for an existing slug, per table.
_VALUE_SYNONYMS: dict[str, dict[str, str]] = {
    "mop_water_levels": {"low": "level_1", "medium": "level_2", "high": "level_3"},
    "mop_wash_temperatures": {"ordinary_temperature": "normal"},
    "dust_collection_frequencies": {"triple": "three_times"},
    "carpet_cleaning_methods": {"self_adaption": "adaptive", "span": "cross"},
}

#: Dock actions a spec template can list for hardware the retail unit lacks.
_DOCK_ACTIONS = frozenset(
    {"start_dust_arrest", "start_mop_wash", "stop_mop_wash", "start_dry", "stop_dry"}
)

#: Work-mode input of the Dreame start-clean, captured on the X20+ (the spec
#: lists only the clean-extend data input).
_DREAME_MODE_PIID = 1

_ENGLISH = REPO / "custom_components" / "xiaomi_vacuum" / "translations" / "en.json"


@dataclass
class Draft:
    """What could be read off a miot-spec instance, plus what needs a human."""

    urn: str
    properties: dict[Property, tuple[int, int]] = field(default_factory=dict)
    actions: dict[str, tuple[int, int, int | None]] = field(default_factory=dict)
    room_sweep: tuple[int, int, int | None] | None = None
    dreame_start_clean: tuple[int, int, int | None] | None = None
    dreame_stop_clean: tuple[int, int, int | None] | None = None
    status: dict[int, StatusSlug | str] = field(default_factory=dict)
    value_tables: dict[str, dict[str, int]] = field(default_factory=dict)
    charging_states: dict[int, str] = field(default_factory=dict)
    booleans: set[Property] = field(default_factory=set)
    todos: list[str] = field(default_factory=list)


def slug(description: str) -> str:
    """Snake-case a value-list description: ``"Go Charging"`` → ``go_charging``."""
    words = re.sub(r"(?<=[a-z])(?=[A-Z0-9])", " ", description.strip())
    return re.sub(r"[^a-z0-9]+", "_", words.casefold()).strip("_")


def _translated_slugs(table: str) -> frozenset[str]:
    node = json.loads(_ENGLISH.read_text(encoding="utf-8"))["entity"]
    for key in _TABLE_TRANSLATIONS[table]:
        node = node.get(key, {})
    return frozenset(node.get("state", {}))


def _known_slug(table: str, name: str, todos: list[str]) -> str:
    """Return the translated slug ``name`` stands for, noting it when there is none."""
    known = _translated_slugs(table)
    synonym = _VALUE_SYNONYMS.get(table, {}).get(name)
    for candidate in (name, f"{name}s", synonym):
        if candidate in known:
            return candidate
    todos.append(f"{table}: {name!r} has no translation yet")
    return name


def _short_type(urn: str) -> str:
    return urn.split(":")[3]


def _brush_side(service: MiotSpecService) -> str | None:
    description = service.get("description", "").casefold()
    if "main" in description:
        return "main"
    if "side" in description:
        return "side"
    return None


def _value_list(prop: MiotSpecProperty) -> list[ValueListEntry]:
    return prop.get("value-list", [])


def draft(instance: MiotSpecInstance) -> Draft:
    """Read every known property, action and value list off ``instance``."""
    result = Draft(urn=instance["type"])
    specs: dict[Property, MiotSpecProperty] = {}
    for service in instance["services"]:
        _draft_service(result, service, specs)
    if Property.FAULT_IDS in result.properties:
        # The plain fault next to a fault-ids list latches the last code.
        result.properties.pop(Property.FAULT, None)
    status = specs.get(Property.STATUS)
    for entry in _value_list(status) if status else []:
        name = slug(entry["description"])
        if name in {status_slug.value for status_slug in StatusSlug}:
            result.status[entry["value"]] = StatusSlug(name)
        elif name in _STATUS_SYNONYMS:
            result.status[entry["value"]] = _STATUS_SYNONYMS[name]
        else:
            result.status[entry["value"]] = entry["description"]
    for name, table in _VALUE_TABLES.items():
        if name in specs and (values := _value_list(specs[name])):
            result.value_tables[table] = {
                _known_slug(table, slug(entry["description"]), result.todos): entry[
                    "value"
                ]
                for entry in values
            }
    if result.dreame_start_clean is not None:
        _adopt_dreame_layout(result)
    if charging := specs.get(Property.CHARGING_STATE):
        result.charging_states = {
            entry["value"]: slug(entry["description"])
            for entry in _value_list(charging)
        }
    _note_what_needs_a_human(result)
    return result


def _note_what_needs_a_human(result: Draft) -> None:
    """Add a TODO for everything the spec alone cannot settle."""
    result.todos.append(
        "replace <product name> in the docstring and in name= with the retail "
        "name (the spec only says what kind of device it is)"
    )
    if dock := sorted(_DOCK_ACTIONS & set(result.actions)):
        result.todos.append(
            f"{', '.join(dock)} come from the spec template: drop the ones the "
            "retail dock has no hardware for (the S40 Pro lists them on a plain "
            "charging dock)"
        )
    if result.charging_states and _CHARGING_SLUG not in result.charging_states.values():
        result.todos.append(
            f"no charging state is {_CHARGING_SLUG!r}: rename the one meaning "
            "charging, or the charging sensor stays off"
        )
    result.todos.extend(
        f"required action {name} not found in the spec: find its address (e.g. "
        "in a Mi Home capture), the module does not load without it"
        for name in _REQUIRED_ACTIONS
        if name not in result.actions
    )
    if result.room_sweep is not None and result.room_sweep[2] is None:
        result.todos.append(
            "the spec's start-vacuum-room-sweep takes no input: find how the app "
            "passes the rooms before wiring room cleaning"
        )


def _adopt_dreame_layout(result: Draft) -> None:
    """Rewire the job actions the way Dreame firmware behind a Xiaomi spec uses them."""
    vacuum_stop = result.actions.get("stop_sweeping")
    if vacuum_stop is not None:
        result.actions["pause_sweeping"] = vacuum_stop
    if result.dreame_stop_clean is not None:
        result.actions["stop_sweeping"] = result.dreame_stop_clean
    if (start := result.actions.get("start_sweep")) is not None:
        result.actions.setdefault("continue_sweep", start)
    result.todos.append(
        "Dreame-built layout: pause is stop-sweeping, stop is the Dreame "
        "stop-clean and start-sweep resumes, as on the X20+ (c102gl.py); confirm "
        "on the device, and check the fault codes, mop status and cleaning mode "
        "against c102gl.py"
    )


def _draft_service(
    result: Draft,
    service: MiotSpecService,
    specs: dict[Property, MiotSpecProperty],
) -> None:
    siid = service["iid"]
    service_type = _short_type(service["type"])
    side = _brush_side(service) if service_type == "brush-cleaner" else None
    for prop in service.get("properties", []):
        prop_type = _short_type(prop["type"])
        if service_type == "brush-cleaner":
            name = _BRUSH_PROPERTIES.get((side, prop_type)) if side else None
            if name is None and prop_type in ("brush-life-level", "brush-left-time"):
                result.todos.append(
                    f"{siid}.{prop['iid']} {prop_type} on brush service "
                    f"{service.get('description')!r}: main or side brush?"
                )
        else:
            name = _PROPERTIES.get((service_type, prop_type))
        if name is not None and name not in result.properties:
            result.properties[name] = (siid, prop["iid"])
            specs[name] = prop
            if prop.get("format") == "bool":
                result.booleans.add(name)
    _draft_actions(result, service, service_type, side)


def _draft_actions(
    result: Draft, service: MiotSpecService, service_type: str, side: str | None
) -> None:
    siid = service["iid"]
    for action in service.get("actions", []):
        action_type = _short_type(action["type"])
        inputs = action.get("in") or []
        input_piid = inputs[0] if isinstance(inputs, list) and inputs else None
        address = (siid, action["iid"], input_piid)
        if action_type == "start-vacuum-room-sweep":
            result.room_sweep = address
            continue
        if (service_type, action_type) == ("vacuum-extend", "start-clean"):
            result.dreame_start_clean = address
            continue
        if (service_type, action_type) == ("vacuum-extend", "stop-clean"):
            result.dreame_stop_clean = address
            continue
        if service_type == "brush-cleaner" and action_type == "reset-brush-life":
            field_name = _BRUSH_ACTIONS.get(side or "")
        else:
            field_name = _ACTIONS.get((service_type, action_type))
        if field_name is not None and field_name not in result.actions:
            result.actions[field_name] = address


def render(model: str, result: Draft) -> str:
    """Render ``result`` as the draft source of ``spec/<model>.py``."""
    short = model.rsplit(".", 1)[-1]
    dreame = result.dreame_start_clean is not None
    room_cleaning = "DreameSegmentClean" if dreame else "DirectRoomSweep"
    lines = [
        '"""',
        f"Spec for the <product name> — ``{model}``.",
        "",
        f"Source: ``{result.urn}``.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from typing import TYPE_CHECKING",
        "",
        *(["from .map_format import DreameMapFormat"] if dreame else []),
        "from .model_actions import ModelActions",
        "from .model_spec import ModelSpec",
        "from .property import Property",
        f"from .room_cleaning import {room_cleaning}",
        "from .status_slug import StatusSlug",
        "",
        "if TYPE_CHECKING:",
        "    from .addresses import MiotPropertyBinding",
        "",
        *[
            line
            for todo in result.todos
            for line in textwrap.wrap(
                f"TODO: {todo}",
                width=79,
                initial_indent="# ",
                subsequent_indent="#   ",
            )
        ],
        "_PROPERTY_MAPPING: dict[Property, MiotPropertyBinding] = {",
    ]
    for name, (siid, piid) in result.properties.items():
        encoding = ""
        if name in result.booleans:
            encoding += ', "boolean": True'
        if name is Property.USER_DEFINE_SWEEP_CONFIG:
            encoding += ', "polled": False'
        lines.append(
            f'    Property.{name.name}: {{"siid": {siid}, "piid": {piid}{encoding}}},'
        )
    lines += ["}", "", "_ACTIONS = ModelActions("]
    for field_name, (siid, aiid, input_piid) in result.actions.items():
        extra = (
            f', "in_piid": {input_piid}'
            if field_name in _INPUT_ACTIONS and input_piid is not None
            else ""
        )
        lines.append(f'    {field_name}={{"siid": {siid}, "aiid": {aiid}{extra}}},')
    lines += [")", "", "_STATUS: dict[int, StatusSlug] = {"]
    for code, status in result.status.items():
        if isinstance(status, StatusSlug):
            lines.append(f"    {code}: StatusSlug.{status.name},")
        else:
            lines.append(f"    # TODO: {code} {status!r} has no StatusSlug")
    lines += ["}", "", f"{short.upper()} = ModelSpec(", f'    model="{model}",']
    lines += [
        '    name="<product name>",',
        "    property_mapping=_PROPERTY_MAPPING,",
        "    actions=_ACTIONS,",
        "    status=_STATUS,",
    ]
    for table, values in result.value_tables.items():
        lines.append(f"    {table}={_mapping(values)},")
    if result.charging_states:
        lines.append(f"    charging_state_slugs={_mapping(result.charging_states)},")
    if result.dreame_start_clean is not None:
        siid, aiid, input_piid = result.dreame_start_clean
        address = (
            f'"siid": {siid}, "aiid": {aiid}, '
            f'"mode_piid": {_DREAME_MODE_PIID}, "data_piid": {input_piid}'
        )
        lines += [
            "    # TODO: the work-mode input is the X20+'s; confirm on the device.",
            "    room_cleaning=DreameSegmentClean(",
            f"        {{{address}}}",
            "    ),",
            "    # TODO: map the map-name property (6.8 on the X20+, unpublished).",
            "    map_format=DreameMapFormat(),",
        ]
    elif result.room_sweep is not None and result.room_sweep[2] is not None:
        siid, aiid, input_piid = result.room_sweep
        lines += [
            "    # TODO: confirm the robot honours the spec's room sweep; the S20+",
            "    # and the Dreame-built X20+ ignore theirs (ADDING_A_MODEL.md §3.7).",
            (
                "    room_cleaning=DirectRoomSweep("
                f'{{"siid": {siid}, "aiid": {aiid}, "in_piid": {input_piid}}}),'
            ),
        ]
    lines.append(")")
    return "\n".join(lines)


def _mapping(values: dict[str, int] | dict[int, str]) -> str:
    """Render a value table as a dict literal in the repository's quote style."""
    items = ", ".join(
        f"{json.dumps(key)}: {json.dumps(value)}" for key, value in values.items()
    )
    return f"{{{items}}}"


def _fetch_json(url: str) -> object:
    with urllib.request.urlopen(url, timeout=_TIMEOUT_SECONDS) as response:  # noqa: S310
        return json.load(response)


def _latest_urn(model: str, version: int | None) -> str:
    index = _fetch_json(_INSTANCES_URL)
    instances = index["instances"] if isinstance(index, dict) else []
    candidates = [
        entry
        for entry in instances
        if entry.get("model") == model
        and (version is None or entry.get("version") == version)
    ]
    if not candidates:
        msg = f"No miot-spec instance published for {model}"
        raise SystemExit(msg)
    released = [entry for entry in candidates if entry.get("status") == "released"]
    return str(max(released or candidates, key=lambda entry: entry["version"])["type"])


def main() -> None:
    """Print the draft for the model named on the command line."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("model")
    parser.add_argument("--version", type=int)
    parser.add_argument("--spec", type=Path)
    arguments = parser.parse_args()
    if arguments.spec is not None:
        instance = json.loads(arguments.spec.read_text(encoding="utf-8"))
    else:
        urn = _latest_urn(arguments.model, arguments.version)
        instance = _fetch_json(_INSTANCE_URL.format(urn=urn))
    print(render(arguments.model, draft(instance)))


if __name__ == "__main__":
    main()
