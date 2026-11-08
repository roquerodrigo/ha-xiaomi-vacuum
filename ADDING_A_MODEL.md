# Adding support for a new vacuum model

This integration supports one vacuum model per `ModelSpec` instance under
[`custom_components/xiaomi_vacuum/spec/`](custom_components/xiaomi_vacuum/spec),
one module per model.
Adding a new model is, by design, **a data-only change**: which entities,
features and `send_command` names a model gets is derived from the properties
it maps and the actions it defines, so no platform code, entity class or
cloud-client change is needed for a model whose properties and actions the
integration already knows.

This document walks through the steps, using a hypothetical
`xiaomi.vacuum.c108gl` (Xiaomi Robot Vacuum X30 Pro) as an example.

---

## 1. Confirm the model is a Xiaomi vacuum

The config flow only discovers devices whose model string starts with
`xiaomi.vacuum.` (see `VACUUM_MODEL_PREFIX` in `const.py`). Anything else
won't even show up in the picker.

---

## 2. Draft the spec from the published miot-spec

Every model publishes its MIoT layout on the public miot-spec service. The
draft generator reads it and prints a first version of the spec module:

```bash
uv run scripts/draft_model.py xiaomi.vacuum.c108gl > custom_components/xiaomi_vacuum/spec/c108gl.py
```

It picks the highest released spec version (`--version N` picks another one,
`--spec FILE` reads a downloaded instance instead) and maps:

- every property and action whose service and URN type the integration
  already knows (`vacuum:status`, `battery:battery-level`,
  `vacuum:start-sweep`, the brush services told apart by their
  description, ...), with their SIID/PIID/AIID, marking the ones the spec
  publishes as `bool` with `"boolean": True`;
- the status codes to `StatusSlug` members, and the fan speed, mode, clean
  times, water level, route and obstacle-avoidance value lists to the slugs
  the translations already have;
- the room sweep to a `DirectRoomSweep`, or, when the spec has the Dreame
  `vacuum-extend:start-clean`, the Dreame layout of the X20+.

What it cannot decide is left as `# TODO:` comments, and `ruff` refuses to
commit a TODO, so each one gets resolved: the retail product name (the spec
only says "Robot Cleaner"), a brush service with no main/side
description, a status description no slug covers, a value with no
translation, charging states without a `charging` one, a required action the
spec does not publish, the dock actions to keep, the room-cleaning flow to
confirm.
The draft is a starting point, not a verified spec — the rest of this guide
is about verifying it.

The spec is not the whole truth. If you can pair the device in the Mi Home app,
capture the app's traffic (Charles proxy on Android, or a `mitmproxy`
capture) — Mi Home sometimes uses a different RPC path than the published
spec, and the capture is the source of truth for what the firmware actually
honours. The S20+ room-clean flow was discovered this way; the spec's direct
`start-vacuum-room-sweep` action exists but the robot ignores it.

---

## 3. Shape the `ModelSpec`

### 3.1 Start from a sibling when one fits

When the new model shares a supported model's layout, derive its spec from
that model with `dataclasses.replace` and state only the differences instead
of keeping the full draft. The S40 Pro (`ov71gl.py`) is the X20 Max without
the dock, zone and custom-cleaning actions (and the custom cleanings list),
with three extra status codes and its own phantom and notice faults:

```python
OV71GL = replace(
    D109GL,
    model="xiaomi.vacuum.ov71gl",
    name="Xiaomi Robot Vacuum S40 Pro",
    actions=replace(D109GL.actions, start_dust_arrest=None, ...),
    status={**D109GL.status, 22: StatusSlug.STATION_ASSISTING_CLEANING, ...},
    ignored_fault_codes=frozenset({100027}),
)
```

To tell whether two models share a layout, draft both and diff the drafts:
identical drafts (apart from the model and the URN) mean the same layout.

A derived spec inherits everything its sibling has and everything it gains
later, so list in its docstring what it removes and why. Which inherited parts
to keep is **the verification rule** this guide uses everywhere:

- Keep what the sibling has verified, as long as the new model's own spec
  publishes it at the same address and the retail hardware has the part.
- Remove what the retail hardware lacks (the S40 Pro's dock actions).
- Without a device, remove the flows that proved model-specific — room
  cleaning (`room_cleaning=None`), zone cleaning (`start_zone_sweep=None`) and
  custom cleanings (`start_user_define_sweep=None` together with the
  `Property.USER_DEFINE_SWEEP_CONFIG` binding; a contract test requires both or
  neither) — and say in the pull request that they wait for a device.
- What the draft maps beyond the verified sibling (e.g. the X20 Max draft's
  consumable hours left and reset actions) is not a difference of the new
  model: leave it out, and add it as a feature once a device confirms it.

The closest siblings: `d109gl.py` for a model with an auto-wash dock,
`ov71gl.py` for an X20-Max-shaped spec without dock hardware, `b108gl.py` for
the S20+ layout, `c102gl.py` for a Dreame-built model.

**Dreame-built models** (the spec puts the job data and a `start-clean` action
in a `vacuum-extend` service at SIID 4) follow `c102gl.py`: a plain uint8
fault, pause on `stop-sweeping`, stop on the Dreame `stop-clean`, no
mode-specific start actions, and a task-status property (`Property.TASK_STATUS`)
that decides the cleaning job instead of the status table. Leave unmapped what
the model packs into a Dreame bitfield, unless a mask can isolate it (§3.2).

**Check the retail hardware, not just the spec.** Xiaomi reuses one spec
template across a product line: the S40 Pro publishes dust-arrest and
mop-wash actions although it ships with a plain charging dock. A defined
action creates its button and `send_command`, so wiring an action the
hardware cannot perform creates a button that does nothing — leave such
actions `None`.

### 3.2 Property mapping

`property_mapping` binds each `Property` to its place on the device:

```python
_PROPERTY_MAPPING: dict[Property, MiotPropertyBinding] = {
    Property.STATUS: {"siid": 2, "piid": 1},
    Property.FAULT: {"siid": 2, "piid": 2},
    Property.SWEEP_MOP_TYPE: {"siid": 4, "piid": 23, "mask": 0x03},
    Property.DO_NOT_DISTURB: {"siid": 5, "piid": 1, "boolean": True},
    Property.USER_DEFINE_SWEEP_CONFIG: {"siid": 2, "piid": 42, "polled": False},
    ...
}
```

Besides the address, a binding says how the value is encoded:

- `mask` — the property owns only those bits of a packed device value. Reads
  expose the bits shifted down; writes keep every other bit as the device
  reports it (the X20+ cleaning mode in the low two bits of `4.23`).
- `boolean` — the device publishes a real bool and expects one back, instead
  of a `0`/`1` integer.
- `polled: False` — the property is read on demand, never in the periodic
  poll (the custom cleanings list, which would push the batched reply past
  the single-datagram limit).

If the model exposes a property no `Property` member exists for, add one to
`Property` first, then see [§3.6](#36-entities-features-and-commands) if it
should back a new entity.

### 3.3 Actions

`ModelActions` holds the action addresses. The job actions (`start_sweep`,
`stop_sweeping`, `return_home`, `pause_sweeping`, `continue_sweep`,
`identify`) are required; every other one stays `None` when the model lacks
it.

### 3.4 Status table

Map each published status code to a `StatusSlug`:

```python
_STATUS: dict[int, StatusSlug] = {
    1: StatusSlug.IDLE,
    2: StatusSlug.CHARGING,
    4: StatusSlug.SWEEPING,
    ...
}
```

A slug means the same on every model, so what it implies lives once, in
`spec/status_catalog.py` (`STATUS_MEANINGS`): the `VacuumActivity` shown in
HA's UI, whether a fresh `start` is safe from it (`is_idle`, the robot is
parked) or should resume the current job, and what it reveals about the
cleaning job (`cleaning_job`). Pick the slug from what the Mi Home app shows
for the code (the `multiLanguage` endpoint in `XIAOMI_VACUUM_API.md` §1,
`zh_cn` first), not from the spec's shorthand name.

Only when a code means something no slug covers, add one: a `StatusSlug`
member, its `StatusMeaning` in `STATUS_MEANINGS`, and its translation under
`entity.sensor.status.state.<slug>`. For the meaning:

- `cleaning_job` is `CleaningJobSignal.IN_PROGRESS` for statuses that only
  happen during a job (cleaning, paused, washing the mop or recharging
  mid-job), `CleaningJobSignal.FINISHED` for statuses that only happen outside
  one (idle, charging, returning to the dock at the end), and
  `CleaningJobSignal.INCONCLUSIVE` for statuses the device reports both mid-job
  and after the job ends (e.g. `station_working`) — those keep the previous
  verdict.
- The activity must **never** be `VacuumActivity.ERROR` — an active fault
  drives that state separately (see `vacuum/cleaner.py:XiaomiVacuum.activity`).
  Status codes that semantically mean "error" but fire during normal cycles map
  to their nearest non-error activity.

Optimistic UI patches report the code of the activity's canonical slug
(`CANONICAL_STATUSES`: `sweeping`, `paused`, `idle`, `go_charging`,
`charging`). The order of `_STATUS` only matters for an activity whose
canonical slug the model lacks: then the first code with that activity wins.

### 3.5 Faults

How the live fault is read follows from the mapping:

- `Property.FAULT_IDS` mapped — the X20 Max style: a `Fault Ids` property
  publishing a JSON list `{"ts": ..., "fault": [code, ...]}` where `[0]` or
  `[]` means no active fault (`FaultIdsReading`). Leave the plain `fault`
  property next to it unmapped: it latches the last code and never resets.
- otherwise `Property.FAULT` — a plain code where `0 == healthy`
  (`PlainFaultReading`).

Xiaomi publishes no code→text table anywhere; the localized message comes
from the cloud message feed and is resolved by the coordinator into
`fault_text` (see `cloud/connector.py:get_device_fault_texts`).

**Phantom faults.** A firmware image is shared across a whole product family,
so a unit sold with less hardware than the family's top model keeps running the
checks for the parts it lacks and reports their failure permanently. The Mi
Home app knows the hardware variant and hides those codes; the integration
cannot infer it, so list them in `ignored_fault_codes` (a `frozenset[int]`,
empty by default). They are dropped before the fault reaches any entity —
without this the vacuum entity sits in `VacuumActivity.ERROR` for the device's
whole life. The S40 Pro is the worked example: it ships with a plain charging
dock and reports `100027` ("Sewage tank is full or not installed") forever.
Only add a code once a real device is observed publishing it while the app
reports nothing wrong.

**Maintenance notices.** Some codes are not faults at all but routine
maintenance: the robot publishes them while the user takes a part out (dust bin
emptied, water tank refilled) and clears them once it is back. List them in
`notice_fault_codes` (a `frozenset[int]`, empty by default). They still reach
the Error / Error code sensors, but the vacuum entity keeps its status-derived
activity instead of switching to `VacuumActivity.ERROR`; a real fault published
alongside one takes precedence. The S40 Pro reports `210005` (dust bin out) and
`210020` (water tank out).

### 3.6 Entities, features and commands

Nothing here is declared per model:

- The vacuum, status, error, error-code and cleaning-in-progress entities
  exist on every model.
- Every other entity is created when its requirement is met
  (`spec/entity_requirements.py`): a mapped property (`PROPERTY_ENTITIES` —
  battery, consumables, selects, switches, volume, map image) or a defined
  action (`ACTION_ENTITIES` — dock and consumable-reset buttons).
- The vacuum advertises area cleaning when the spec has a room-cleaning flow
  and fan speeds when it has a `fan_speeds` table.
- The `send_command` names are the actions in `spec/send_commands.py` the
  model defines.

**Value tables** (`fan_speeds`, `sweep_mop_types`, `clean_times`,
`mop_water_levels`, `charging_state_slugs`, `sweep_routes`,
`obstacle_avoidances`) are per-model fields, filled exactly when the matching
property is mapped. Shared tables live in `spec/enumerations.py`; copy one
into the model's own module the moment the new vacuum publishes a different
one.

**Adding a new entity** (rare):

1. Add the `Property` (or the `ModelActions` field) it reads.
2. Add the `EntityKey` and its requirement to `PROPERTY_ENTITIES` or
   `ACTION_ENTITIES`.
3. Implement the entity class on the relevant platform and add it to that
   platform's `_*_CLASSES` registry (e.g. `_SELECT_CLASSES` in
   `select/__init__.py`).
4. Add translations for the entity and its states.

### 3.7 Room cleaning

`room_cleaning` names the flow that starts a room clean, carrying the actions
it invokes (`spec/room_cleaning/`):

- `DirectRoomSweep(action)` — the device honours a single
  `start-vacuum-room-sweep` taking the room ids as input (X20 Max).
- `ConfigThenCustomSweep(set_room_clean_configs, start_custom_sweep)` —
  captured from the Mi Home app on the S20+: mark the target rooms via
  `set-room-clean-configs`, then fire `start-custom-sweep`. Both steps go
  through the cloud when a session is available — local UDP routinely times
  out on the multi-step sequence.
- `DreameSegmentClean(action)` — Dreame-built models: the generic
  `start-clean` with the segment work mode and a
  `{"selects": [[room, repeat, fan, water, order], ...]}` room selection. The
  X20+ acknowledges its spec-published `start-room-sweep` but ignores it.
- `None` — no room cleaning; the vacuum does not offer area cleaning.

Without a device or a capture, set `room_cleaning=None` (the verification rule
in §3.1): `DirectRoomSweep` is only the first flow to try *on* a device, and
the S20+ and the X20+ both ignore their spec-published direct action. A flow
none of these covers becomes a new `RoomCleaning` subclass, run against the
`RoomCleaningDevice` port the API client implements.

### 3.8 Map format

`map_format` decodes the cloud map blob and says where the room list comes
from: `XiaomiMapFormat()` (the default) decrypts the Xiaomi payload and takes
the rooms from the room-information property; `DreameMapFormat()` decodes the
Dreame frame, whose segment metadata lists the rooms.

### 3.9 Register the model

Import it in `spec/registry.py` and add it to `MODELS`:

```python
from .c108gl import C108GL

MODELS: dict[str, ModelSpec] = {
    D109GL.model: D109GL,
    B108GL.model: B108GL,
    OV71GL.model: OV71GL,
    C102GL.model: C102GL,
    C108GL.model: C108GL,
}
```

Re-export it from `spec/__init__.py` as well, so tests can import it from the
package root like the existing models.

That's it. The integration now recognises the new model — the cloud action
endpoint (`/miotspec/action`) is model-agnostic, and the platform setup
functions consult `spec.entities` to decide which entities to create.

---

## 4. Translations

New status slugs, value slugs or entities need their keys in every file under
`custom_components/xiaomi_vacuum/translations/` (their key sets must stay in
sync — see `CODE_STYLE.md`):

- Status slugs → `entity.sensor.status.state.<slug>`
- Select option slugs → `entity.select.<select_key>.state.<slug>`
- New entity names → `entity.<platform>.<key>.name`

A test fails when a `StatusSlug` has no translation.

---

## 5. Tests

Add one entry to `MODEL_FIXTURES` in [`tests/conftest.py`](tests/conftest.py):
the parsed state the mocked device publishes (take it from a real unit when
you can — every polled property needs a key), a distinct MAC so entries don't
collide on `unique_id`, a host and a name. Add the model to the pinned set in
`test_registry_lists_all_supported_models` (`tests/test_spec.py`).

That alone runs [`tests/test_model_contract.py`](tests/test_model_contract.py)
and the other per-model tests against the new model: status and fault mapped,
no two properties on one address, a status code for every activity the
vacuum patches optimistically, value tables exactly for the mapped
properties, a sample state covering every polled property, and a setup that
creates every entity the spec lists.

Then add `tests/models/test_c108.py` for what is specific to the model,
mirroring [`test_d109.py`](tests/models/test_d109.py) /
[`test_c102.py`](tests/models/test_c102.py): the entities it must and must not
have (e.g. no dust-arrest button without an auto-dust dock), the action
addresses its commands hit, its fault payload, and its room-cleaning payload
(or, with `room_cleaning=None`, that the vacuum does not offer area cleaning).
Set the model up with the `setup_model` fixture — `entry, device = await
setup_model("xiaomi.vacuum.c108gl")` — so it needs no named fixtures of its
own.

---

## 6. Verify

Run the full CI mirror locally before opening a PR:

```bash
uv run ruff format .
uv run ruff check . --fix
uv run mypy custom_components/xiaomi_vacuum
uv run pytest
```

The coverage gate is 90 %.

---

## 7. Edge cases worth knowing

- **Unknown model at setup.** If the device handshake returns a model the
  integration doesn't know, `get_spec()` falls back to the default spec
  (`DEFAULT_MODEL`) so local control stays usable, and a Repair issue is
  raised in Settings → Repairs prompting the user to file an issue. This
  means **adding a model after the fact is forward-compatible**: existing
  users with that vacuum will simply reload the integration to pick it up.
- **Spec version bumps.** Xiaomi occasionally publishes a new spec version
  (`urn:...:c108gl:2`) that shifts PIIDs or adds services. If the new
  version is the only one installable on the device, update the existing
  `ModelSpec` in place (cite the urn in the docstring); otherwise consider a
  separate `C108GL_V2` entry and a model-string match rule.
- **The Mi Home app is the source of truth.** When the spec and the app's
  captured traffic disagree, trust the app — it's what users run. The
  room-cleaning flows exist precisely to encode such deviations.
