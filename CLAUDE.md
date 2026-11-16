# ha-xiaomi-vacuum

Home Assistant custom integration for the **Xiaomi Robot Vacuum X20 Max**
(`xiaomi.vacuum.d109gl`), **Xiaomi Robot Vacuum S20+** (`xiaomi.vacuum.b108gl`),
**Xiaomi Robot Vacuum S40 Pro** (`xiaomi.vacuum.ov71gl`) and the Dreame-built
**Xiaomi Robot Vacuum X20+** (`xiaomi.vacuum.c102gl`), domain
`xiaomi_vacuum`. Public repo, distributed through the Home Assistant
Marketplace.

Read `README.md` for the user-facing feature list and setup flow,
`XIAOMI_VACUUM_API.md` for the device's MIoT API reference, and
`ADDING_A_MODEL.md` for the step-by-step on extending support to a new vacuum.
Two project skills under `.claude/skills/` drive the common changes:
**`add-model`** (supporting a new `xiaomi.vacuum.*` model) and **`add-feature`**
(a new entity, service or `send_command`, or exposing a property or action).
Use them for that work.
**Always read `CODE_STYLE.md` before adding or restructuring code** — it is
the enforced style guide (one class per file/entity, strict typing, naming,
property conventions, etc.) and takes precedence over anything not covered
here.

## Architecture

- **Local control, cloud-assisted setup.** Day-to-day polling/control is
  `iot_class: local_polling` over MIoT via `xiaomi-vacuum-sdk`. The Xiaomi cloud
  (`custom_components/xiaomi_vacuum/cloud/`) is used only for the QR-login
  setup flow, the map image, localized error text, and the X20+ room list
  (decoded from its Dreame cloud map, `DreameMapFormat`, by the
  SDK's `DreameMapDecoder`).
- **Entity platforms**, each its own subpackage under
  `custom_components/xiaomi_vacuum/`: `vacuum/`, `image/`, `sensor/`,
  `binary_sensor/`, `select/`, `button/`, `switch/`, `number/`. Every concrete entity is its own
  class in its own file (see `CODE_STYLE.md` — no generic
  `EntityDescription`-with-`value_fn` pattern).
- **`api/`** wraps the local MIoT client; **`cloud/`** wraps the Xiaomi cloud
  (QR login, device discovery, map fetch, error-message resolution).
- **`spec/`** — per-model MIoT spec registry: one `ModelSpec` module per model
  plus `registry.py` for the model-string lookup. A `ModelSpec` bundles its
  property mapping (each `MiotPropertyBinding` carries the address plus the
  encoding: `mask`, `boolean`, `polled`), action mapping, a status table that
  maps codes to `StatusSlug` members (what a slug means — activity, idle,
  cleaning-job signal — lives once in `status_catalog.py`), the value tables,
  phantom/notice fault codes, and three behaviour objects: the room-cleaning
  flow (`spec/room_cleaning/`, run against the `RoomCleaningDevice` port the
  API client implements), the map format (`spec/map_format/`) and the fault
  reading (`spec/fault_reading/`, derived from which fault property is
  mapped). Nothing else is declared: the entities to create (`spec.entities`)
  follow from `entity_requirements.py` — a base roster plus every entity whose
  property is mapped or whose action is defined — and the `send_command`
  names from the defined actions (`send_commands.py`). Platforms filter their
  `_*_CLASSES` registries by `EntityKey in spec.entities`, so adding a new
  model is a data-only change: one module (drafted by `scripts/draft_model.py`
  from the published miot-spec), its `registry.py` and `spec/__init__.py`
  lines, and one `MODEL_FIXTURES` entry in the tests (see
  `ADDING_A_MODEL.md`). A sibling model is derived with `dataclasses.replace`
  (the S40 Pro from the X20 Max). The spec is selected from the device model
  at setup and threaded through `runtime_data` / the coordinator. **Read the
  model's module before touching any SIID/PIID/AIID** — layouts diverge from
  model to model, and each module's docstring says how it differs from its
  closest sibling.
- **`config_flow.py`** — QR-login config flow plus reauth (fresh QR scan when
  the stored cloud session expires) and a reconfigure flow for changing the
  Xiaomi cloud region.
- **`repairs.py`** — per-entry repair issues, each cleared automatically once
  the condition resolves: `cannot_connect` when the vacuum is unreachable
  (setup tolerates this and still serves the map) and `unsupported_model` when
  the handshake reports a model with no `ModelSpec`, which falls back to the
  default spec so local control keeps working.
- **`translations/`** — one JSON file per locale, `en.json` the source; all
  user-facing strings live here, never hardcoded in Python.

## Generic vs model-specific

Most contributions come from someone who owns one model and fixes or extends
it for that model. Every change must first decide where it belongs: put it in
the wrong place and one vacuum's quirk reaches every vacuum, or a shared
capability gets reimplemented per model. Apply this section when writing a
change **and** when reviewing a pull request.

**The rule: mechanisms are generic, facts are per model.**

| Generic — every model runs it | Per model — `spec/<model>.py` |
|---|---|
| Entity classes, platforms, vacuum services, `send_command` dispatch | SIID/PIID/AIID addresses and their encoding (`mask`, `boolean`, `polled`) |
| Reading and writing a property, the optimistic-update pattern | Value tables (fan speeds, modes, intervals...) and the status table |
| The coordinators, the API client, the cloud client and its features | Fault code sets: phantom (`ignored_fault_codes`), notices (`notice_fault_codes`) |
| The `ModelSpec` fields and the behaviour strategies themselves | Which actions are wired, which strategy the model uses (room cleaning, map format) |

1. **Generic code never knows a model.** No test of the model string, and no
   model-specific address, status code, fault code or command name outside
   `spec/<model>.py`. A capability is gated by data: the model maps the
   property or defines the action (`entity_requirements.py`,
   `send_commands.py`). A hardcoded set of command names or codes in
   `vacuum/`, `api/` or a platform is the smell to look for.
2. **Data differs → a `ModelSpec` field; behaviour differs → a strategy.**
   A new field names a concept any model could have (`notice_fault_codes`),
   never a switch for one model's feature. When models need different code
   paths, add a subclass under `spec/room_cleaning/`, `spec/map_format/` or
   `spec/fault_reading/`, chosen by the spec.
3. **Device payloads are decoded once**, by the strategy that owns them.
   Consumers ask the spec (`live_fault_code`, `cleaning_job_signal`, ...);
   they never re-parse the `fault_ids` JSON or re-derive what a status
   means. If a consumer needs more (every active code, not just the first),
   extend the strategy.
4. **A generic feature works on every model, or degrades gracefully** (no
   entity, a translated refusal), and its tests cover every
   `MODEL_FIXTURES` entry. Shared touchpoints — `vacuum/cleaner.py`,
   `api/client.py`, the coordinators — serve all models: a change made there
   for one model must be expressed through the spec, and must leave every
   other code path untouched.
5. **Model facts need evidence from that model**: a physical unit (the value
   observed, the firmware), or the verification rule of `ADDING_A_MODEL.md`
   §3.1 (the model's own published spec at the same address, plus a sibling's
   verification). Spec-only claims get a footnote in the README matrix. An
   observation never spreads to other models: a fault code seen on the S40
   Pro does not go into the X20 Max.
6. **Derived specs inherit.** `ov71gl.py` is `replace(D109GL, ...)`, and
   models derived from the S40 Pro inherit from it in turn. Anything added
   to a parent reaches every descendant, so review each one and remove what
   its hardware lacks. A change meant for one model goes in that model's
   module, not in its parent.
7. **Mirror the device, don't add policy.** The integration reports what the
   firmware publishes and forwards commands. It does not duplicate safeguards
   the firmware already enforces (refusing a start the robot itself refuses)
   or invent interpretations nobody observed on a device.

Questions for every review: does generic code now know about a specific
model? Is every model fact backed by evidence from that model? Was a change
to a parent spec reviewed for its descendants? Can a generic change break or
silently no-op on a model the author does not own?

## Environment & tooling

- Python **>= 3.14.2**, dependency management via **`uv`** (`uv.lock`
  committed, `[tool.uv] package = false`).
- Dependency groups in `pyproject.toml`: `dev` (HA test harness, pytest,
  `xiaomi-vacuum-sdk`) and `lint` (`ruff`, `mypy`).
- Local dev setup is `uv sync --all-groups` (there is no setup script;
  dependencies live in `pyproject.toml`). A bare `uv sync` installs only the
  `dev` group — there is no `tool.uv.default-groups` — so `ruff`/`mypy` from
  `lint` would be missing.
- `scripts/develop` — runs a real local HA instance against this
  integration (`config/` dir, symlink-free via `PYTHONPATH`).
- `scripts/qr_test.py` — standalone CLI to exercise the Xiaomi cloud QR-login
  flow outside of HA, for debugging the cloud connector.
- `scripts/draft_model.py` — prints a draft spec module for a new model from
  its published miot-spec, leaving what it cannot decide as `TODO` comments.

## Commands

Run before committing — CI mirrors these (`ruff` → `pytest`, `validate`):

```bash
uv run ruff format .
uv run ruff check . --fix
uv run mypy custom_components/xiaomi_vacuum
uv run pytest
```

- `tests/test_model_contract.py` runs invariants against every registered
  model; each model has one `MODEL_FIXTURES` entry in `tests/conftest.py`.
- `pytest` config lives in `pyproject.toml`: `pytest-homeassistant-custom-component`
  harness, `asyncio_mode = "auto"`, coverage gate **`--cov-fail-under=90`**
  over `custom_components/xiaomi_vacuum`.
- `ruff` targets `py314`, `select = ["ALL"]` with a short ignore list; test
  files get relaxed rules (see `[tool.ruff.lint.per-file-ignores]`).
- `mypy` is strict: no `Any`, no bare generics, `disallow_untyped_defs` —
  relaxed only for `tests/*`.
- `pre-commit install` wires local `uv run` hooks (`ruff format`,
  `ruff check --fix`, `mypy`) — always the versions pinned in
  `pyproject.toml` — plus standard hygiene hooks (trailing whitespace,
  YAML/JSON/TOML checks, LF line endings).

## CI (`.github/workflows/`, one file per concern)

Every job calls a reusable workflow from `roquerodrigo/workflows`, tracking
`@main` (no version pinning — the workflows repo is same-owner and changes
there take effect here immediately). The exceptions run same-owner actions at
`@latest` instead: the `validate` job (`roquerodrigo/home-assistant-autopilot`)
and the release job (`roquerodrigo/release-autopilot`, then
`home-assistant-autopilot` with `command: publish` to attach the release zip).

- `ci.yml` — `lint` → `tests` + `validate` in parallel (both need `lint`),
  then `update-pr-branch` once all three pass (pull requests only).
- `release.yml` — Release Autopilot, triggered by `workflow_run` after CI
  succeeds on a push to `main`. It is decoupled from `ci.yml`, not a job in
  it, so a red CI never cuts a release.
- `codeql.yml` — weekly (Sunday) plus every push/PR.
- `auto-assign.yml` — opened/reopened issues and PRs (plus manual dispatch,
  no schedule) assign the maintainer and request their review. Uses
  `pull_request_target`, so it needs no checkout of fork code.

Required checks are named `<job id> / <workflow job name>` — renaming a job id
silently un-requires its check in branch protection.

## Conventions worth knowing

- **HA version floor is `2026.4.4`** — segment-to-area cleaning depends on
  `VacuumEntityFeature.CLEAN_AREA` and the `Segment` dataclass introduced in
  2026.3. Don't use vacuum APIs older than that without checking compat.
  `hacs.json` pins the same floor.
- **Xiaomi cloud region is user-selectable** via the config flow and the
  reconfigure flow — never assume it is hard-coded.
- **Two coordinators, not one** — local device state and the cloud map image
  poll independently on different cadences/failure domains. Don't merge them.
- **Optimistic UI**: vacuum actions apply state changes immediately in the
  entity, then a background refresh confirms against the device ~5s later.
  Preserve this pattern when adding new commands.
- This repo is **public with branch protection** — new work goes on a feature
  branch and lands via PR with green CI; no direct pushes to `main`, and the
  protection is never lowered to land a quick fix. Only *Rebase and merge* is
  enabled.
- `CONTRIBUTING.md` references a VS Code devcontainer (`.devcontainer.json`)
  originally derived from the `integration_blueprint` template — still valid
  for spinning up a sandboxed HA dev instance.
