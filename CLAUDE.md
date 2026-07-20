# ha-xiaomi-vacuum

Home Assistant custom integration for the **Xiaomi Robot Vacuum X20 Max**
(`xiaomi.vacuum.d109gl`), domain `xiaomi_vacuum`. Public repo, HACS-distributed.

Read `README.md` for the user-facing feature list and setup flow, and
`XIAOMI_VACUUM_API.md` for the device's MIoT API reference. **Always read
`CODE_STYLE.md` before adding or restructuring code** — it is the enforced
style guide (one class per file/entity, strict typing, naming, property
conventions, etc.) and takes precedence over anything not covered here.

## Architecture

- **Local control, cloud-assisted setup.** Day-to-day polling/control is
  `iot_class: local_polling` over MIoT via `python-miio`. The Xiaomi cloud
  (`custom_components/xiaomi_vacuum/cloud/`) is used only for the QR-login
  setup flow, the map image, and localized error text.
- **Entity platforms**, each its own subpackage under
  `custom_components/xiaomi_vacuum/`: `vacuum/`, `image/`, `sensor/`,
  `binary_sensor/`, `select/`, `button/`. Every concrete entity is its own
  class in its own file (see `CODE_STYLE.md` — no generic
  `EntityDescription`-with-`value_fn` pattern).
- **`api/`** wraps the local MIoT client; **`cloud/`** wraps the Xiaomi cloud
  (QR login, device discovery, map fetch, error-message resolution).
- **`coordinator.py`** — local device state polling (`DataUpdateCoordinator`).
- **`map_coordinator.py`** — separate coordinator for the cloud-rendered map
  image, decoupled from local polling.
- **`cached_device_info.py`** — persists device info discovered during setup.
- **`config_flow.py`** — QR-login config flow plus a reconfigure flow for
  changing the Xiaomi cloud region.
- **`repairs.py`** — raises a repair issue when the vacuum is offline at
  setup (setup tolerates this and still serves the map).
- **`translations/`** — `en.json` and `pt-BR.json`; all user-facing strings
  live here, never hardcoded in Python.

## Environment & tooling

- Python **>= 3.14.2**, dependency management via **`uv`** (`uv.lock`
  committed, `[tool.uv] package = false`).
- Dependency groups in `pyproject.toml`: `dev` (HA test harness, pytest,
  `python-miio`, `vacuum-map-parser-xiaomi`) and `lint` (`ruff`, `mypy`).
- `scripts/setup` is stale and broken — it installs `requirements.txt`,
  which was removed when CI migrated to `uv` (dependencies now live in
  `pyproject.toml`). Use `uv sync` for local dev instead.
- `scripts/develop` — runs a real local HA instance against this
  integration (`config/` dir, symlink-free via `PYTHONPATH`).
- `scripts/qr_test.py` — standalone CLI to exercise the Xiaomi cloud QR-login
  flow outside of HA, for debugging the cloud connector.

## Commands

Run before committing — CI mirrors these (`ruff` → `pytest`, `validate`):

```bash
uv run ruff format .
uv run ruff check . --fix
uv run mypy custom_components/xiaomi_vacuum
uv run pytest
```

- `pytest` config lives in `pyproject.toml`: `pytest-homeassistant-custom-component`
  harness, `asyncio_mode = "auto"`, coverage gate **`--cov-fail-under=90`**
  over `custom_components/xiaomi_vacuum`.
- `ruff` targets `py314`, `select = ["ALL"]` with a short ignore list; test
  files get relaxed rules (see `[tool.ruff.lint.per-file-ignores]`).
- `mypy` is strict: no `Any`, no bare generics, `disallow_untyped_defs` —
  relaxed only for `tests/*`.
- `pre-commit install` wires `ruff-check --fix` + `ruff-format` plus standard
  hygiene hooks (trailing whitespace, YAML/JSON/TOML checks, LF line endings).

## CI (`.github/workflows/ci.yml`)

Reusable workflows from `roquerodrigo/.github@v2`: `lint` → `tests` +
`validate` (parallel, both need `lint`) → `release` (release-please, on push
to `main`). Also `codeql` (weekly + on push/PR) and `auto-assign` /
`update-pr-branch` for PR housekeeping.

## Conventions worth knowing

- **HA version floor is `2026.4.4`** — segment-to-area cleaning depends on
  `VacuumEntityFeature.CLEAN_AREA` and the `Segment` dataclass introduced in
  2026.3. Don't use vacuum APIs older than that without checking compat.
  `hacs.json` pins the same floor.
- **Xiaomi cloud region is user-selectable** (via config flow + reconfigure
  flow) — do not assume it's hard-coded; that was true before the
  `feat/cloud-region-selection` change and is no longer accurate.
- **Two coordinators, not one** — local device state and the cloud map image
  poll independently on different cadences/failure domains. Don't merge them.
- **Optimistic UI**: vacuum actions apply state changes immediately in the
  entity, then a background refresh confirms against the device ~5s later.
  Preserve this pattern when adding new commands.
- This repo is **public with branch protection** — per the user's global
  git conventions, new work goes on a feature branch and lands via PR with
  green CI; no direct pushes to `main`.
- `CONTRIBUTING.md` references a VS Code devcontainer (`.devcontainer.json`)
  originally derived from the `integration_blueprint` template — still valid
  for spinning up a sandboxed HA dev instance.
