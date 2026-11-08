---
name: add-feature
description: Add a feature to this Xiaomi vacuum integration — a new sensor, binary sensor, switch, select, number or button, a new vacuum service or send_command, or exposing a property or action a model already publishes. Use when asked to add, expose or wire an entity, setting, command or service, including when a new model needs something the integration does not know yet.
---

# Add a feature

Read [`CODE_STYLE.md`](../../../CODE_STYLE.md) first: one class per file and per
entity, strict typing, no comments that restate the code, every user-facing
string in the translations. [`ADDING_A_MODEL.md`](../../../ADDING_A_MODEL.md)
§3 describes the spec fields named below.

Features are gated by data, never by model: an entity exists on a model
because the model maps the property or defines the action it needs. Never test
the model string in platform code.

## 1. Locate the device side

Find the property or action on every supported model that publishes it. The
URN of each model's spec is in its module docstring (`Source:`); list its
services with:

```bash
curl -s 'https://miot-spec.org/miot-spec-v2/instance?type=<urn>' | jq '.services[]
  | {siid: .iid, service: .type, description,
     properties: [.properties[]? | {piid: .iid, type, format, unit, "value-list"}],
     actions: [.actions[]? | {aiid: .iid, type, in}]}'
```

The published spec says where it is; the Mi Home app says whether the firmware
honours it. Note per model the address, the format (`bool`, `uint8`, ...),
the value list and the unit. A model whose retail hardware lacks the part does
not map it.

## 2. Classify and follow the checklist

### A. Entity backed by a property (sensor, switch, select, number, image)

1. `spec/property.py`: a `Property` member.
2. Each model module that publishes it: the binding in `_PROPERTY_MAPPING`,
   with `"boolean": True` for a bool, `"mask"` for bits of a packed value,
   `"polled": False` for a value read on demand only. A derived spec
   (`ov71gl.py`) inherits its sibling's binding — remove it there if the
   derived model lacks the part.
3. `spec/entity_key.py`: an `EntityKey` member.
4. `spec/entity_requirements.py`: `Property.X: EntityKey.Y` in
   `PROPERTY_ENTITIES`.
5. The entity class, in its own file under the platform package, on the
   closest base: `_XiaomiVacuumPropertySensor` (integer as is),
   `_XiaomiVacuumTimeLeftSensor`, `_XiaomiVacuumLifeSensor`,
   `_XiaomiVacuumSwitch`, `_XiaomiVacuumSelect`. Its `unique_id` is
   `{entry_id}_{translation_key}`; never change an existing one.
6. The platform's `_<PLATFORM>_CLASSES` registry and `__all__`.
7. `data.py`: the key in the `VacuumState` TypedDict.
8. A select also needs a value table: a `ModelSpec` field (in `MAPPING_FIELDS`)
   filled by each model that maps the property, the reverse lookup if the
   entity needs one, the `_VALUE_TABLES` entry in
   `tests/test_model_contract.py`, and the `_VALUE_TABLES` /
   `_TABLE_TRANSLATIONS` entries in `scripts/draft_model.py`.

### B. Button firing an action

1. `spec/model_actions.py`: an optional field (`... | None = None`).
2. Each model that has it: the address in its `ModelActions`.
3. `EntityKey` member, and `"field_name": EntityKey.Y` in `ACTION_ENTITIES`.
4. A class on `_XiaomiVacuumActionButton` with `_action_name` and
   `_attr_translation_key`; register it in `_BUTTON_CLASSES`.

### C. `send_command` name

A parameterless action worth calling from automations: add its `ModelActions`
field name to `SEND_COMMAND_ACTIONS` in `spec/send_commands.py`. It is offered
on every model that defines the action.

### D. Vacuum service (like `clean_zone`)

1. `services.yaml`: the service, its fields and selectors.
2. `vacuum/__init__.py`: the schema and `async_register_entity_service`.
3. `vacuum/cleaner.py`: the entity method. Refuse with
   `ServiceValidationError(translation_domain=DOMAIN, translation_key=...)`
   when the spec lacks what it needs, and validate input before any device
   call.
4. `api/client.py`: the device call, raising `XiaomiVacuumApiClientError`
   with a `"Failed to <verb> <object>: <cause>"` message.
5. Translations under `services.<service>` and `exceptions.<key>`; the icon
   under `services` in `icons.json`.

### E. New platform

`PLATFORMS` in the integration `__init__.py`, a platform package with a
`_<PLATFORM>_CLASSES` registry filtered by `spec.entities`, and that registry
in `_PLATFORM_CLASSES` of `tests/test_model_contract.py`.

### F. New behaviour variant

A room-cleaning flow, map format or fault representation the existing classes
do not cover: a subclass in `spec/room_cleaning/`, `spec/map_format/` or
`spec/fault_reading/`, chosen by the model's spec. A room-cleaning flow talks
to the device only through the `RoomCleaningDevice` port.

## 3. Common to every feature

- **Generator:** teach `scripts/draft_model.py` where the new property or action
  lives (`_PROPERTIES`, `_BRUSH_PROPERTIES`, `_ACTIONS`), so future drafts map
  it. `tests/test_draft_model.py` fails until you do.
- **Translations:** the entity name under `entity.<platform>.<translation_key>`
  (and its states) in **every** file under `translations/` — the key sets must
  match.
- **Icons:** `icons.json` under `entity.<platform>.<translation_key>`.
- **Commands:** apply the change optimistically with `_patch_state` and call
  `_schedule_refresh()` so the device confirms it.
- **Tests:** the entity behaviour (value, write, unavailable or None input) and,
  in `tests/models/`, presence on the models that map it and absence on the
  ones that do not. Extend `MODEL_FIXTURES` states with the new key.
- **Docs:** a row in the README "What each model supports" matrix and the
  feature list; `ADDING_A_MODEL.md` when the spec gains a field.

## 4. Verify and commit

```bash
uv run ruff format .
uv run ruff check . --fix
uv run mypy custom_components/xiaomi_vacuum
uv run pytest
```

Confirm on a real unit of each model that gains the feature: the value matches
the Mi Home app, a write reaches the device and survives the next poll, and no
other entity changed. Commit as `feat(<scope>): <what users get>` on a branch
and open a pull request.

## Done when

- [ ] The feature is gated by a mapped property or a defined action, never by model
- [ ] Every model that publishes it maps it; derived specs reviewed
- [ ] Generator knows it; translations in every locale; icon set
- [ ] Tests for the behaviour and for presence and absence per model
- [ ] README matrix updated
- [ ] All four gates pass and the feature is verified on a device
