---
name: add-feature
description: Add a feature to this Xiaomi vacuum integration — a new sensor, binary sensor, switch, select, number or button, a new vacuum service or send_command, or exposing on a model a property or action it publishes (including an entity another model already has). Use when asked to add, expose or wire an entity, setting, command or service, including when a new model needs something the integration does not know yet.
---

# Add a feature

Read [`CODE_STYLE.md`](../../../CODE_STYLE.md) first: one class per file and per
entity, strict typing, no comments that restate the code, every user-facing
string in the translations. [`ADDING_A_MODEL.md`](../../../ADDING_A_MODEL.md)
§3 describes the spec fields named below; its §3.1 holds **the verification
rule** for what a model may claim without a device.

Features are gated by data, never by model: an entity exists on a model
because the model maps the property or defines the action it needs. Never test
the model string in platform code.

## 1. Locate the device side

Find the property or action on every supported model that publishes it. The
URN of each model's spec is in its module docstring (`Source:`); list one
service of it with:

```bash
curl -s 'https://miot-spec.org/miot-spec-v2/instance?type=<urn>' | jq '.services[]
  | select(.iid == <siid>)
  | {siid: .iid, service: .type, description,
     properties: [.properties[]? | {piid: .iid, type, format, unit, access, "value-list", "value-range"}],
     actions: [.actions[]? | {aiid: .iid, type, in}]}'
```

(Drop the `select` line to list every service.) The published spec says where
it is; the Mi Home app says whether the firmware honours it. Note per model the
address, the format (`bool`, `uint8`, ...), the access, the value list or
range and the unit. A model whose retail hardware lacks the part does not map
it.

## 2. Is the entity already there?

If the `Property` (or `ModelActions` field) **and** its entry in
`spec/entity_requirements.py` already exist — another model has the entity —
the feature is data only:

- the binding or action address in each model module that gains it (A.2 / B.2
  below), plus the derived-spec review there;
- the tests and docs in §4.

Skip the rest of §3: the class, registry, `VacuumState` key, translations,
icons and generator entries exist already.

## 3. Otherwise, classify and follow the checklist

A feature can be several types at once (a sensor and a reset button).

### A. Entity backed by a property (sensor, switch, select, number, image)

1. `spec/property.py`: a `Property` member.
2. Each model module that publishes it: the binding in `_PROPERTY_MAPPING`,
   with `"boolean": True` for a bool, `"mask"` for bits of a packed value,
   `"polled": False` for a value read on demand only.
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
   filled by each model that maps the property, the `_VALUE_TABLES` entry in
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

### New entities only

- **Generator:** teach `scripts/draft_model.py` where the new property or
  action lives (`_PROPERTIES`, `_BRUSH_PROPERTIES`, `_ACTIONS`,
  `_BRUSH_ACTIONS`), or list it in `_NOT_DRAFTED` in `tests/test_draft_model.py`
  with the reason. That test fails until you do one or the other.
- **Translations:** the entity name under `entity.<platform>.<translation_key>`
  (and its states) in **every** file under `translations/` — the key sets must
  match.
- **Icons:** `icons.json` under `entity.<platform>.<translation_key>`.
- **Commands:** apply the change optimistically with `_patch_state` and call
  `_schedule_refresh()` so the device confirms it.

## 4. Every feature

- **Derived specs:** `ov71gl.py` is built with `replace(D109GL, ...)` and
  `replace(D109GL.actions, ...)`, so it inherits every binding and action added
  to the X20 Max. Apply the verification rule there: keep what its own spec
  publishes at the same address on hardware it has; otherwise remove the
  binding or set the action to `None`.
- **Sample states:** add the key to the state of every model that maps it in
  `tests/conftest.py`. `SAMPLE_STATE` feeds the X20 Max, the S40 Pro (through
  `{**SAMPLE_STATE, ...}`) and the `sample_state` fixture; `_SAMPLE_STATE_B108`
  and `_SAMPLE_STATE_C102` are separate. `test_the_sample_state_covers_every_polled_property`
  fails until you do.
- **Pinned entity sets:** tests in `tests/models/` pin the exact entities of a
  platform per model (e.g. `{s.entity_id for s in hass.states.async_all("button")} == {...}`,
  or `== []`); update them on every model that gains the entity, derived ones
  included.
- **Draft extras:** `test_x20_max_draft_holds_every_hand_written_address` lists
  what the X20 Max draft maps beyond `D109GL`; wiring one of those on the X20
  Max shrinks that list.
- **Tests:** a new entity class gets its behaviour tests (value, write, None or
  unavailable input) next to the platform's tests. An existing class wired to
  another model gets, in `tests/models/test_<model>.py`, its value from the
  fixture, a press or write hitting that model's address, and its presence;
  models that do not map it assert its absence.
- **Docs:** the README "What each model supports" matrix (add a row or tick the
  model's cell) and the Models column of the entity table under "Features"
  (and of the `send_command` table for a command); `ADDING_A_MODEL.md` when the
  spec gains a field; the mapped marks in `XIAOMI_VACUUM_API.md` when it
  documents that service.

## 5. Verify and commit

```bash
uv run ruff format .
uv run ruff check . --fix
uv run mypy custom_components/xiaomi_vacuum
uv run pytest
```

Confirm on a real unit of each model that gains the feature: the value matches
the Mi Home app, a write reaches the device and survives the next poll, and no
other entity changed. Without a unit, keep the change to what the model's
published spec has, and say in the pull request which models and entities are
unverified. Commit as `feat(<scope>): <what users get>` on a branch and open a
pull request.

## Done when

- [ ] The feature is gated by a mapped property or a defined action, never by model
- [ ] Every model that publishes it maps it; derived specs reviewed with the verification rule
- [ ] New entities: generator taught, translations in every locale, icon set
- [ ] Sample states, pinned entity sets and per-model presence/absence tests updated
- [ ] README matrix and Models columns updated
- [ ] All four gates pass; verified on a device, or the pull request says what is not
