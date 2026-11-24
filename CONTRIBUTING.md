# Contributing

Bug reports, ideas and pull requests are welcome.

## Reporting a bug

Open an [issue](https://github.com/roquerodrigo/ha-xiaomi-vacuum/issues/new/choose)
with:

- the Home Assistant version, the integration version and the vacuum model;
- what you did, what you expected and what happened;
- the diagnostics downloaded from the integration's menu (the token and the
  Xiaomi sign-in are redacted) and the relevant log lines.

To ask for a model that is not supported yet, use the model support request
form on the same page.

## Development setup

The project uses [uv](https://docs.astral.sh/uv/) and Python 3.14.2 or newer.

```bash
uv sync --all-groups         # install the dependencies, including ruff and mypy, into .venv
uv run scripts/develop       # run Home Assistant at http://localhost:8123 with this integration loaded
```

A plain `uv sync` leaves out the `lint` group, so `ruff` and `mypy` would be
missing. `scripts/develop` uses the configuration in [`config/`](config/).

Two more scripts help with cloud and model work:

- `uv run scripts/qr_test.py [region]` runs the Xiaomi QR sign-in outside
  Home Assistant.
- `uv run scripts/draft_model.py <model>` prints a first draft of the spec
  module for a new model from its published MIoT spec.

## Checks

Run these before opening a pull request. CI runs the same ones, and
`pre-commit install` runs the first three on every commit.

```bash
uv run ruff format .                           # format
uv run ruff check . --fix                      # lint
uv run mypy custom_components/xiaomi_vacuum    # type-check
uv run pytest                                  # tests, coverage must stay at 90 % or more
```

Read [CODE_STYLE.md](CODE_STYLE.md) before adding or restructuring code.

## Adding a model or a feature

- [ADDING_A_MODEL.md](ADDING_A_MODEL.md) walks through supporting a new
  `xiaomi.vacuum.*` model, from the draft spec to the tests.
- [XIAOMI_VACUUM_API.md](XIAOMI_VACUUM_API.md) documents the MIoT properties,
  actions and cloud endpoints the integration uses.

A change for one model goes in that model's spec module, and every model fact
needs evidence from a real unit of that model. Settings that only the
published spec shows get a footnote in the README model table.

## Pull requests

1. Fork the repository and branch from `main`.
2. Write commit messages as [Conventional Commits](https://www.conventionalcommits.org/).
   Releases and their notes are generated from them. Mark breaking changes
   with `!` or a `BREAKING CHANGE:` footer.
3. When you change user-facing strings, update every file in
   `custom_components/xiaomi_vacuum/translations/` (`en.json` is the source).
   A test fails when their keys differ.
4. Update the README when behaviour, configuration, entities or supported
   models change.
5. Fill in the pull request template.

## License

Contributions are released under the project's [MIT License](LICENSE).
