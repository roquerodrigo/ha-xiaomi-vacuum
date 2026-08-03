# Adding support for a new vacuum model

This integration supports one vacuum model per `ModelSpec` instance under
[`custom_components/xiaomi_vacuum/spec/`](custom_components/xiaomi_vacuum/spec),
one module per model.
Adding a new model is, by design, **a data-only change** — no platform code,
entity classes, or cloud-client changes are needed for a model whose
capabilities are already represented by the `Capability` / `EntityKey` enums.

This document walks through the steps, using a hypothetical
`xiaomi.vacuum.c108gl` (Xiaomi Robot Vacuum X30 Pro) as an example.

---

## 1. Confirm the model is a Xiaomi vacuum

The config flow only discovers devices whose model string starts with
`xiaomi.vacuum.` (see `VACUUM_MODEL_PREFIX` in `const.py`). Anything else
won't even show up in the picker.

---

## 2. Pull the device's miot-spec

Capabilities are not hardcoded — they are published on the public miot-spec
service. Fetch them with the model's `urn`:

1. Look up the `urn` for the model:
   ```
   https://miot-spec.org/miot-spec-v2/instances?status=all
   ```
   Find the entry whose `model == "xiaomi.vacuum.c108gl"` and copy its `urn`.
2. Fetch the full spec:
   ```
   https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-c108gl:1
   ```
3. Note the **current spec version** (the `:1` at the end). If multiple
   versions exist, use the highest one — older firmware may not be flashable.

You'll get a JSON document with a list of services (`services[]`), each
containing `properties[]` and `actions[]`. You need:

- the **SIID + PIID** of every property the integration reads/writes
- the **SIID + AIID** of every action it invokes
- the value-list enumerations for `fan_speed`, `mode`, etc.
- the published status codes (look for a property named `status` of type
  `uint8`/`uint16` with a `value-list`)

If you can pair the device in the Mi Home app, capture the app's traffic
(Charles proxy on Android, or a `mitmproxy` capture) — Mi Home sometimes
uses a different RPC path than the published spec, and the capture is the
source of truth for what the firmware actually honours. The S20+
`config_then_custom` room-clean flow was discovered this way; the spec's
direct `start-vacuum-room-sweep` action exists but the robot ignores it.

---

## 3. Add the `ModelSpec` entry

Create `custom_components/xiaomi_vacuum/spec/c108gl.py`, named after the model
string. Mirror the structure of the closest sibling (`d109gl.py` for a model
with an auto-wash dock, `b108gl.py` for one without).

### 3.1 Property mapping

Build a `dict[Property, MiotPropertyAddress]` keyed by the
`Property` enum. If the new model exposes a property that no enum entry
exists for, add one to `Property` first:

```python
class Property(StrEnum):
    ...
    NEW_THING = "new_thing"
```

Then declare the per-model mapping:

```python
_PROPERTY_MAPPING: dict[Property, MiotPropertyAddress] = {
    Property.STATUS: {"siid": 2, "piid": 1},
    Property.FAULT: {"siid": 2, "piid": 2},  # plain uint32 like the S20+
    Property.SWEEP_MOP_TYPE: {"siid": 2, "piid": 3},
    ...
}
```

If the model has a property **only it exposes** (e.g. a new obstacle
sensor), add the `Property` enum entry, add the mapping here, and see
[§3.6 Capabilities](#36-capabilities--entity-gating) below if it should
gate a new entity.

### 3.2 Actions

Declare a `ModelActions(...)`. Required actions must all be present;
**optional** ones (dock-only, room-clean-strategy-specific) stay `None`
when the model lacks them — the integration handles `None` gracefully.

```python
_ACTIONS = ModelActions(
    start_sweep={"siid": 2, "aiid": 1},
    stop_sweeping={"siid": 2, "aiid": 2},
    return_home={"siid": 3, "aiid": 1},  # like the S20+ battery.start-charge
    ...
    # No auto-wash dock on this hypothetical model:
    start_mop_wash=None,  # implicit default
    start_dry=None,
)
```

### 3.3 Status table

Each published status code must have an entry in `status`. Pick the
closest-matching `VacuumActivity` for HA's UI; the `slug` is a stable
translation key (see [§4 Translations](#4-translations)).

`is_idle` decides whether a fresh `start` is safe (the vacuum is parked at
the dock) versus whether `start` should resume an in-progress clean.

```python
_STATUS: dict[int, StatusDef] = {
    1: {"activity": VacuumActivity.IDLE, "slug": "idle", "is_idle": True},
    2: {"activity": VacuumActivity.DOCKED, "slug": "charging", "is_idle": True},
    4: {"activity": VacuumActivity.CLEANING, "slug": "sweeping", "is_idle": False},
    ...
}
```

The activity must **never** be `VacuumActivity.ERROR` for any status code —
an active fault drives that state separately (see
`vacuum/cleaner.py:XiaomiVacuum.activity`). Status codes that semantically
mean "error" but fire during normal cycles map to their nearest non-error
activity.

### 3.4 Fault representation

Set `fault_kind`:

- `"ids"` — the X20 Max style: a `Fault Ids` property publishing a JSON list
  `{"ts": ..., "fault": [code, ...]}` where `[0]` means no active fault.
  Wire `Property.FAULT_IDS` in the property mapping. The coordinator parses
  the list and extracts the first non-zero code.
- `"simple"` — the S20+ style: a plain `fault` uint32 property where
  `0 == healthy`. Wire `Property.FAULT` in the property mapping. The
  coordinator reads it directly.

Xiaomi publishes no code→text table anywhere; the localized message comes
from the cloud message feed and is resolved by the coordinator into
`fault_text` (see `cloud/connector.py:get_device_fault_texts`).

### 3.5 Room cleaning strategy

Set `room_clean_strategy`:

- `"direct"` — the device honours a single `start-vacuum-room-sweep` action
  taking room ids as input. Wire `actions.start_room_sweep` (with its
  `in_piid`).
- `"config_then_custom"` — captured from the Mi Home app: mark the target
  rooms via `set-room-clean-configs` (pushing a `room_attrs` JSON), then
  fire `start-custom-sweep` with no params. Wire `actions.set_room_clean_configs`
  and `actions.start_custom_sweep`. This flow is routed through the cloud
  when a session is available — local UDP routinely times out on the
  multi-step sequence.

If you can't capture the app flow, start with `"direct"` and verify with a
real device; the S20+ ignored its spec-published direct action.

### 3.6 Capabilities & entity gating

`capabilities` is **derived** automatically from the spec — you do not
need to declare it. The rules are:

| Capability           | Derived from                                            |
| -------------------- | ------------------------------------------------------- |
| `DUST_ARREST`        | `actions.start_dust_arrest is not None`                 |
| `SWEEP_ROUTE`        | `Property.SWEEP_ROUTE in property_mapping`              |
| `OBSTACLE_AVOIDANCE` | `Property.OBSTACLE_AVOIDANCE_STRATEGY in property_mapping` |

Each capability gates one entity (see `_CAPABILITY_ENTITIES`); base entities
(vacuum, sensors, binary sensor, map image, default selects) are always
present (see `_BASE_ENTITIES`). Every platform filters its `_*_CLASSES`
registry by `EntityKey in spec.entities`, so the entity-key set is the single
source of truth for what a model exposes.

> **Note:** mop-wash / dry dock actions exist on the X20 Max but are **not** a
gating capability — they don't create an entity. They're exposed only through
`send_commands` (see the X20 Max spec for an example).

**Per-model enumerations.** `sweep_routes` and `obstacle_avoidances` live on
the `ModelSpec` (alongside `fan_speeds` / `sweep_mop_types` / `clean_times` /
`mop_water_levels`), not as module-level globals. Populate them when the model
exposes the matching property; leave them empty (the default) otherwise.

**Adding a new capability** (rare):

1. Add the `Capability` enum entry.
2. Add a derivation rule in `ModelSpec.capabilities`.
3. Add the `EntityKey` for the entity it gates, and add it to
   `_CAPABILITY_ENTITIES` so it's auto-created when the capability is set.
4. Implement the entity class on the relevant platform and add it to that
   platform's `_*_CLASSES` registry (e.g. `_SELECT_CLASSES` in
   `select/__init__.py`).
5. Add translations for the entity + its states.

For most new models this is unnecessary — you only fill in
`ModelSpec(...)`, and capability derivation takes care of itself.

### 3.7 Final `ModelSpec(...)` block

```python
C108GL = ModelSpec(
    model="xiaomi.vacuum.c108gl",
    name="Xiaomi Robot Vacuum X30 Pro",
    property_mapping=_PROPERTY_MAPPING,
    actions=_ACTIONS,
    status=_STATUS,
    fan_speeds=dict(FAN_SPEEDS),  # reuse shared enums where identical
    sweep_mop_types=dict(SWEEP_MOP_TYPES),
    clean_times={"one_time": 1, "two_times": 2},  # if this model only has 2
    mop_water_levels={"off": 0, "level_1": 1, "level_2": 2, "level_3": 3},
    send_commands={
        "start_only_sweep": _ACTIONS.start_only_sweep,
        "start_mop": _ACTIONS.start_mop,
        ...
    },
    charging_state_slugs=dict(CHARGING_STATE_SLUGS),
    fault_kind="simple",
    room_clean_strategy="config_then_custom",
)
```

Shared value tables (`FAN_SPEEDS`, `SWEEP_MOP_TYPES`, `CLEAN_TIMES`,
`CHARGING_STATE_SLUGS`, `SWEEP_ROUTES`, `OBSTACLE_AVOIDANCES`) live in
`spec/enumerations.py`. Copy one into the model's own module the moment the
new vacuum publishes a different table — every enumeration is a per-model
field, never a global the models happen to share.

### 3.8 Register the model

Import it in `spec/registry.py` and add it to `MODELS`:

```python
from .c108gl import C108GL

MODELS: dict[str, ModelSpec] = {
    D109GL.model: D109GL,
    B108GL.model: B108GL,
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

If the model introduces **new status slugs**, **new enum values**, or
**new entities**, add the corresponding keys to both
`custom_components/xiaomi_vacuum/translations/en.json` and
`translations/pt-BR.json` (their key sets must stay in sync — see
`CODE_STYLE.md`):

- Status slugs → `entity.sensor.status.state.<slug>`
- Select option slugs → `entity.select.<select_key>.state.<slug>`
- New entity names → `entity.<platform>.<key>.name`

Slugs that only this model produces but other models don't are fine —
unused keys are harmless; missing keys show as the raw slug in the UI.

---

## 5. Tests

Add `tests/models/test_c108.py` mirroring the existing
[`test_d109.py`](tests/models/test_d109.py) /
[`test_b108.py`](tests/models/test_b108.py). At minimum:

- The right `ModelSpec` is selected (`spec.model == "..."`).
- The expected capability set is derived.
- The expected entity set is created (and absent ones are not — e.g. no
  dust-arrest button if the model has no auto-dust dock).
- Model-specific action addresses are hit when calling the relevant service
  (e.g. `return_to_base` → the right SIID/AIID for this model's dock
  service).
- The fault-parsing branch (`fault_kind="ids"` vs `"simple"`) works for a
  sample payload.

You'll also need a fixture for the new model. Copy the
`mock_miot_device_b108` fixture from
[`tests/conftest.py`](tests/conftest.py) and adapt the sample state /
model string.

---

## 6. Verify

Run the full CI mirror locally before opening a PR:

```bash
uv run ruff format .
uv run ruff check . --fix
uv run mypy custom_components/xiaomi_vacuum
uv run pytest
```

The coverage gate is 90 %; per-model tests typically push it well above
that. If you added a `Property` / `EntityKey` / `Capability` enum entry,
expect to also exercise it in `tests/test_spec.py`.

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
  `ModelSpec` in place (cite the urn in the comment block); otherwise
  consider a separate `C108GL_V2` entry and a model-string match rule.
- **The Mi Home app is the source of truth.** When the spec and the app's
  captured traffic disagree, trust the app — it's what users run. The
  `room_clean_strategy` literal exists precisely to encode such deviations.
