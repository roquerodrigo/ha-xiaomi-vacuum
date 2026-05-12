# Code Style Guide

Style conventions for the `ha-xiaomi-vacuum` project. Run `scripts/lint`
before committing — it executes `ruff format`, `ruff check --fix` and `mypy`,
and must exit cleanly. `pytest` (with the 95 % coverage gate) follows.

**Always read this file before adding or restructuring code.**

## Language

- Code is written in **English**: file names, class names, function names,
  variable names, dictionary keys, identifier strings.
- The conversation language with the user can be Portuguese or anything else;
  what is committed to disk stays English.
- User-facing strings live in `custom_components/xiaomi_vacuum/translations/{en,pt-BR}.json`
  only — never hardcoded in Python.

## File organization

- **One top-level class per file.** Multiple semantically related classes (e.g.
  exception families, sensor entities for one platform) get grouped into a
  package directory with one class per submodule and an `__init__.py`
  re-exporting the public symbols.
- **TypedDicts and `type` aliases do not count as "classes"** for this rule —
  they live alongside related code and don't need their own file.
- **Helper functions** may live in the same file as the single class that uses
  them.
- **`__init__.py` of the integration package** wires `async_setup_entry`,
  `async_unload_entry`, `async_reload_entry` and nothing else.

## Entities: one class per entity

- **One class per entity.** Every entity gets its own dedicated class — never
  share a generic class parameterized by an `EntityDescription` subclass with
  callable fields like `value_fn` or `action_fn`. Encode the entity's behaviour
  directly in its class via `@property` and class-level `_attr_*` constants.
  - Don't write a `XiaomiVacuumSensorDescription` subclass with a `value_fn`
    field.
  - Do write `XiaomiVacuumStatusSensor`, `XiaomiVacuumBatterySensor`,
    `XiaomiVacuumStartButton`, `XiaomiVacuumFanSelect`, etc.
- The reason: each entity is a discrete contract; mixing them through a
  generic class hides the contract behind indirection and discourages per-entity
  refinement (icons, state attributes, custom logic).

## Naming

- Public classes are prefixed with `XiaomiVacuum`.
- Concrete platform entities end with the entity type:
  `XiaomiVacuumSensor`, `XiaomiVacuumButton`, `XiaomiVacuumSelect`,
  `XiaomiVacuumImage`.
- Exception classes end with `Error`.
- Private attributes / functions are prefixed with `_`.

## Typing

**Strict typing. No generics, no `Any`.** Mypy on `scripts/lint` enforces this.

Banned: `typing.Any`, `object` as a value type, bare `dict` / `list` / `tuple` /
`set`, `dict[str, Any]`, `Mapping[str, Any]`.

Required:

- `TypedDict` for known dict / JSON shapes.
- `@dataclass` for structured records.
- Named `type` aliases for recursive / shared shapes — `JsonPrimitive`,
  `JsonValue`, `JsonObject`.
- `frozenset[str]` / `tuple[str, ...]` for fixed string collections.
- `cast("TypedDictName", value)` at HA framework boundaries that hand us a
  permissive type (e.g. `entry.data` is `MappingProxyType[str, Any]`).

When narrowing an HA-provided callback signature, mypy reports `[override]`
(Liskov violation). Add `# type: ignore[override]` with a one-line comment
explaining the deliberate narrowing.

## Properties and `__init__`

- **Always prefer `@property`** over assigning `_attr_*` values in `__init__`.
  Properties are computed lazily from backing fields stored on the parent class
  (e.g. `self.coordinator`, `self.entity_description`).
- When the body of `__init__` would only call `super().__init__(...)`, omit
  `__init__` entirely and let Python inherit the parent.
- Class-level constants like `_attr_attribution = ATTRIBUTION` and
  `_attr_has_entity_name = True` are fine — they don't depend on instance
  state.

## Imports

- Always start every module with `from __future__ import annotations` so type
  hints become lazy strings.
- Same-package relative imports (`from .module import …`) are the default.
- Move type-only imports into a `TYPE_CHECKING` block (Ruff `TC001`/`TC003`):

  ```python
  from __future__ import annotations
  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
      from collections.abc import Mapping
      from miio import Vacuum
  ```

- `noqa` comments are reserved for unavoidable framework constraints. Never
  silence to "make ruff happy" — fix the underlying code.

## Docstrings

- Every public class, function, method (including `@property`) and `__init__`
  has a docstring. Ruff enforces this via `D102`/`D107`.
- A single sentence is usually enough. Describe the *contract* or the *why*,
  not the obvious implementation.
- Module-level docstring at the top of every `.py` file.
- Avoid restating the type — the signature already does that.

## Comments

- Default to **no comments**. Add one only when the *why* is not obvious from
  the code: a hidden constraint, a workaround, a subtle invariant, or a
  deliberate type-system override.
- Never describe *what* the code does — well-named identifiers handle that.
- **No section dividers** like `# --- API payloads ---` to group related
  declarations. If a file has so many sections that you feel the need for
  visual separators, split it into multiple files instead.

## Logging

- Each module uses the package-level `LOGGER` from `const.py`
  (`LOGGER: Logger = getLogger(__package__)`); never call `logging.getLogger(...)`
  ad-hoc.
- Use **lazy `%`-formatting**, never f-strings — they force string interpolation
  even when the level is filtered:

  ```python
  LOGGER.warning("Map fetch failed: %s", exception)   # ✓
  LOGGER.warning(f"Map fetch failed: {exception}")    # ✗
  ```

- Levels:
  - `debug` — successful fetch summaries, every-poll diagnostics.
  - `info` — one-shot lifecycle (setup complete, reauth flow started).
  - `warning` — recoverable failures (transient API error, falling back).
  - `error` / `exception` — unrecoverable in current cycle.
- Never log secrets (`token`, `cloud password`). Wrap upstream exceptions in
  the API-client boundary so their string forms don't leak.

## Error messages

- Format: `"Failed to <verb> <object>: <cause>"`. Keep them short and grep-able.
- Pre-validate inputs before the network call so user-facing errors point at
  the bad input.
- Custom exceptions get the same hierarchy: base → `…CommunicationError`
  (timeout, connection, DNS) → `…AuthenticationError` (cloud login failure,
  token mismatch). Wrap raw upstream errors at the API client boundary;
  everything above only catches the custom hierarchy.

## Coordinators and runtime data

- All API state flows through `entry.runtime_data`
  (`data.py`). Never store integration state in `hass.data`.
- This integration runs **two coordinators**: `coordinator.py` for status
  (vacuum state, battery, etc.) and `map_coordinator.py` for the cleaning-map
  image, decoded via `vacuum-map-parser-xiaomi`. Each polls at its own
  cadence; the map coordinator only refreshes when there is a fresh map id.
- The coordinator is typed as `DataUpdateCoordinator[<TypedDict>]`.
  `_async_update_data` returns the typed payload; client errors map to
  `UpdateFailed`, authentication errors to `ConfigEntryAuthFailed` (which
  triggers reauth).

## Config / repairs / diagnostics

- `config_flow.py` carries `user`, `reauth`, `reauth_confirm` and
  `reconfigure` steps, all sharing one `_validate` helper and one
  `_credentials_schema` builder. The user provides the LAN `host` + `token`
  pair (and optional cloud credentials for map decoding).
- `diagnostics.py` redacts `token`, `cloud_username`, `cloud_password`,
  `cloud_country` via `async_redact_data` (driven by `TO_REDACT: frozenset[str]`).

## Translations

- Two locales: `en.json` and `pt-BR.json`. Their nested key sets must stay
  in sync.
- Issue strings live under `issues.<issue_id>`; flow strings under
  `config.step.<step_id>`; entity names under `entity.<platform>.<key>.name`.

## Pre-commit hooks

`pre-commit` is a dev dependency (`requirements.txt`) and `.pre-commit-config.yaml`
mirrors `scripts/lint` (ruff format, ruff check, mypy). Install once per
clone:

```bash
pre-commit install
```

The hook runs the same gates as CI on every commit. Skip it only on
emergency `git commit --no-verify` and immediately re-run `scripts/lint`.

## Conventional commits

All commits follow [Conventional Commits](https://www.conventionalcommits.org/),
which `release-please` parses to bump the version and generate `CHANGELOG.md`:

| Type | Meaning | Bump |
|---|---|---|
| `feat` | New feature | minor |
| `fix` | Bug fix | patch |
| `perf` | Performance improvement | patch |
| `deps` | Dependency bump | patch |
| `docs` | Documentation only | none |
| `refactor` | Refactor without behavior change | none |
| `test` | Test-only change | none |
| `ci` | CI / tooling change | none |
| `chore` | Anything else (rarely) | none |

- Subject line: imperative mood, lowercase, no trailing period.
- Use scopes when useful: `fix(map): handle missing cloud token`.
- A `BREAKING CHANGE:` footer (or `!` after type) bumps the major version.

## Linting and verification

- Ruff configuration lives in `.ruff.toml` with `select = ["ALL"]`.
- Mypy configuration lives in `mypy.ini`. Both run from `scripts/lint`.
- After every change run `scripts/lint && pytest`. Both gates mirror CI
  (`.github/workflows/lint.yml` + `tests.yml`).
- Tests live in `tests/`, mirroring the production layout. The 95 % coverage
  gate (`pytest.ini`) prevents untested code from sneaking in. When a test
  exercises a state that is impossible under the new types, update or remove
  it — never weaken the type to satisfy the test.
