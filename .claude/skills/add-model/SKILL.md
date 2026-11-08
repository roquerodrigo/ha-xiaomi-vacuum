---
name: add-model
description: Add support for a new Xiaomi vacuum model (a `xiaomi.vacuum.*` model string) to this integration. Use when asked to support, add or wire a new model, when working on a model support issue, or when a user reports the `unsupported_model` repair. Drafts the spec from the published miot-spec, resolves what the draft cannot decide, registers the model, tests it and documents it.
---

# Add a vacuum model

The reference for every field named here is [`ADDING_A_MODEL.md`](../../../ADDING_A_MODEL.md);
the coding rules are in [`CODE_STYLE.md`](../../../CODE_STYLE.md). Read both
before starting. This skill is the order of work and the definition of done,
not a second copy of them.

A model is data: one `ModelSpec` module under
`custom_components/xiaomi_vacuum/spec/`. Entities, features and
`send_command` names are derived from what it maps. If the model needs a
property, action, entity or service the integration does not know yet, do that
part with the `add-feature` skill first, then come back here.

## 1. Gather the inputs

- The model string exactly as the handshake reports it (`xiaomi.vacuum.c108gl`),
  the retail product name, the firmware version and the cloud region it is
  registered in.
- What the retail unit ships with: dock type (plain charger, self-emptying,
  mop washing), mop pads, anything the spec template may list that the
  hardware lacks.
- When a real unit is available: its diagnostics download and the state it
  publishes in each robot state (docked, cleaning, paused, returning, washing).
  When none is, say so — the model cannot be verified, only drafted.

## 2. Draft the spec

```bash
uv run scripts/draft_model.py xiaomi.vacuum.c108gl > custom_components/xiaomi_vacuum/spec/c108gl.py
```

The module is named after the part of the model string after the last dot.
The generator picks the highest released spec version (`--version N` for
another, `--spec FILE` for a downloaded instance). Read the whole draft before
editing it.

## 3. Choose the shape

Compare the draft with the supported models (`ADDING_A_MODEL.md` §3.1):

- **Same layout as a supported model** → replace the draft with
  `dataclasses.replace(<SIBLING>, ...)` stating only the differences, like
  `ov71gl.py`. List in the docstring everything it removes and why: a derived
  spec inherits whatever its sibling gains later.
- **Dreame-built** (the draft says "Dreame-built layout") → compare every line
  with `c102gl.py`: fault codes, mop status, cleaning mode bitfield, map name.
- **Otherwise** → keep the draft and finish it.

## 4. Resolve every TODO

`ruff` rejects TODO comments, so none survives. For each kind:

| TODO | What to do |
|---|---|
| Brush service: main or side? | Decide from the service description or the Mi Home app; map both properties of each service |
| Status description with no `StatusSlug` | Use the closest existing slug by what the app shows (`multiLanguage`, `zh_cn` first); add a slug only for a genuinely new state (`ADDING_A_MODEL.md` §3.4) |
| Value with no translation | Reuse an existing slug when it means the same; otherwise add the slug to every locale |
| Charging state without `charging` | Rename the slug of the state that means charging |
| Required action not found | Find it in a Mi Home capture; the module does not load without it |
| Dock actions from the spec template | Keep only what the retail dock can perform; set the rest to `None` |
| Room sweep to confirm / no input | Confirm on a device which flow the robot honours (§3.7); without one, leave `room_cleaning` as `None` rather than guess |
| Dreame work mode / map name | Confirm on a device, as above |

Then set by hand what no spec publishes: `name`, the docstring (source URN and
every divergence from the closest sibling), `ignored_fault_codes` and
`notice_fault_codes` (only codes observed on a real unit, §3.5).

## 5. Register

- `spec/registry.py`: import and add to `MODELS`.
- `spec/__init__.py`: import and add to `__all__`.

## 6. Test

- `tests/conftest.py`: one `MODEL_FIXTURES` entry — a distinct MAC, a host, a
  name and the parsed state. Take the state from a real unit when there is one;
  it needs a key for every polled property.
- `tests/test_spec.py`: add the model to `test_registry_lists_all_supported_models`.
- `tests/models/test_<short>.py`: only what is specific to the model — the
  entities it must and must not have, the action addresses its commands hit,
  its fault payload, its room-cleaning payload. Mirror `test_c102.py` or
  `test_ov71.py`; build its fixtures with `_patch_miot_client` and
  `_setup_model_entry` like `setup_integration_c102`.

`tests/test_model_contract.py` then runs every invariant against the new model
on its own. Do not weaken a contract test to make a model pass — fix the spec.

## 7. Document

- `README.md`: the supported-models table and the "What each model supports"
  matrix, with a footnote for anything partial.
- `CLAUDE.md`: the model list in the first paragraph and the "Read the model's
  module" warning in the `spec/` paragraph.
- `XIAOMI_VACUUM_API.md`: a section for the model when it has quirks worth
  recording (captures, ignored actions, dead ends).

## 8. Verify and commit

```bash
uv run ruff format .
uv run ruff check . --fix
uv run mypy custom_components/xiaomi_vacuum
uv run pytest
```

On a real unit, with the integration's debug logging on, confirm:

- every entity the spec lists is created and none stays unavailable or unknown;
- the status sensor follows the robot through docked, cleaning, paused,
  returning and (when it has one) dock washing;
- start, pause, resume, stop, return and locate do what they say;
- the map renders and the room list matches the app;
- room cleaning cleans the requested rooms in the requested order;
- the fault sensors stay at 0 when the app shows nothing wrong.

Commit as `feat(spec): add <product name> (<model string>)` on a branch and
open a pull request. State plainly in it what could not be verified on a
device.

## Done when

- [ ] No TODO left; every divergence from the closest sibling is in the docstring
- [ ] Registered in `registry.py` and `spec/__init__.py`
- [ ] `MODEL_FIXTURES` entry, pinned registry test and a model test file
- [ ] README tables and `CLAUDE.md` updated
- [ ] All four gates pass
- [ ] Verified on a real unit, or the pull request says what was not
