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

**The verification rule** (`ADDING_A_MODEL.md` §3.1) decides what goes in when
there is doubt: keep what a supported sibling has verified when this model's
own spec publishes it at the same address and the retail hardware has the part;
without a device, leave out room cleaning, zone cleaning and custom cleanings;
never add what only the draft maps.

## 1. Gather the inputs

- The model string exactly as the handshake reports it (`xiaomi.vacuum.c108gl`).
- The retail product name and what it ships with: dock type (plain charger,
  self-emptying, mop washing), mop pads. The miot-spec only says "Robot
  Cleaner"; look the model code (`C108GL`) up on the mi.com product and spec
  pages or the Mi Home device page.
- The cloud region it is sold for: export-only models are not served by the
  Mainland China cloud (the S40 Pro), which the README notes.
- When a real unit is available: its firmware version, its diagnostics
  download and the state it publishes in each robot state (docked, cleaning,
  paused, returning, washing). When none is, say so — the model can be
  drafted and wired, not verified.

## 2. Draft the spec

```bash
uv run scripts/draft_model.py xiaomi.vacuum.c108gl > custom_components/xiaomi_vacuum/spec/c108gl.py
```

The module is named after the part of the model string after the last dot.
The generator picks the highest released spec version (`--version N` for
another, `--spec FILE` for a downloaded instance). Read the whole draft, and
write down every TODO in it before changing anything: step 4 decides each one
even if the draft itself is replaced.

## 3. Choose the shape

Draft the closest supported models too and diff the drafts:

```bash
uv run scripts/draft_model.py xiaomi.vacuum.d109gl | diff - custom_components/xiaomi_vacuum/spec/c108gl.py
```

- **Identical apart from the model and the URN** → same layout. Replace the
  draft with `dataclasses.replace(<SIBLING>, ...)`, like `ov71gl.py`, overriding
  what the verification rule removes. A derived spec inherits the sibling's
  room cleaning, zone and custom cleanings and dock actions silently. List in
  its docstring everything it removes and why.
- **Dreame-built** (the draft says "Dreame-built layout") → keep the draft and
  compare every line with `c102gl.py`: fault codes, mop status, cleaning-mode
  bitfield, map name.
- **Otherwise** → keep the draft and finish it.

Whatever the shape, what the draft maps beyond the hand-written sibling (the
X20 Max draft has consumable hours left and reset actions the X20 Max spec does
not wire) is not a difference of the new model. Leave it out; it is a feature
for later.

## 4. Resolve every TODO

`ruff` rejects TODO comments, so none survives. For each kind:

| TODO | What to do |
|---|---|
| `<product name>` | Put the retail name in the docstring and in `name=` |
| Brush service: main or side? | Decide from the service description or the Mi Home app; map both properties of each service |
| Status description with no `StatusSlug` | Use the closest existing slug by what the app shows (`multiLanguage`, `zh_cn` first); add a slug only for a genuinely new state (`ADDING_A_MODEL.md` §3.4) |
| Value with no translation | Reuse an existing slug when it means the same; otherwise add the slug to every locale |
| Charging state without `charging` | Rename the slug of the state that means charging |
| Required action not found | Find it in a Mi Home capture; the module does not load without it |
| Dock actions from the spec template | Keep only what the retail dock can perform; set the rest to `None` |
| Room sweep to confirm / no input | Without a device, `room_cleaning=None`; with one, confirm which flow the robot honours (§3.7) |
| Dreame work mode / map name | Confirm on a device; without one, leave room cleaning and the map out |

Then write the docstring (source URN and every divergence from the closest
sibling) and set `ignored_fault_codes` / `notice_fault_codes` — only codes
observed on a real unit (§3.5).

## 5. Register

- `spec/registry.py`: import and add to `MODELS`.
- `spec/__init__.py`: import, add to `__all__`, and add the model to the list
  in the module docstring.

## 6. Test

- `tests/conftest.py`: one `MODEL_FIXTURES` entry — a distinct MAC, a host, a
  name and the parsed state. Take the state from a real unit when there is one,
  and say in a comment when it is borrowed from a sibling; it needs a key for
  every polled property.
- `tests/test_spec.py`: add the model to `test_registry_lists_all_supported_models`.
- `tests/models/test_<short>.py`: only what is specific to the model — the
  entities it must and must not have, the action addresses its commands hit,
  its fault payload, and its room-cleaning payload (or, with
  `room_cleaning=None`, that the vacuum does not offer area cleaning). Set it
  up with `entry, device = await setup_model("xiaomi.vacuum.c108gl")`; no named
  fixtures are needed. Mirror `test_d109.py` or `test_c102.py`.

`tests/test_model_contract.py` then runs every invariant against the new model
on its own. Do not weaken a contract test to make a model pass — fix the spec.

## 7. Document

- `README.md`: the supported-models table, the "What each model supports"
  matrix (with a footnote for anything partial), and the Models column of the
  entity table under "Features" and of the `send_command` table.
- `CLAUDE.md`: the model list in the first paragraph.
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
open a pull request. State plainly in it what was not verified on a device and
what the verification rule left out for that reason.

## Done when

- [ ] No TODO left; the docstring lists every divergence from the closest sibling
- [ ] The verification rule applied: nothing unverified that it excludes, nothing only the draft maps
- [ ] Registered in `registry.py` and `spec/__init__.py` (including its docstring)
- [ ] `MODEL_FIXTURES` entry, pinned registry test and a model test file
- [ ] README tables and `CLAUDE.md` updated
- [ ] All four gates pass
- [ ] Verified on a real unit, or the pull request says what was not
