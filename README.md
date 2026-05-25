# Xiaomi Vacuum for Home Assistant

[![CI](https://github.com/roquerodrigo/ha-xiaomi-vacuum/actions/workflows/ci.yml/badge.svg)](https://github.com/roquerodrigo/ha-xiaomi-vacuum/actions/workflows/ci.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Open your Home Assistant instance and open the repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=roquerodrigo&repository=ha-xiaomi-vacuum&category=integration)

A **100% local** [Home Assistant](https://www.home-assistant.io/) integration for the
**Xiaomi Robot Vacuum X20 Max** (`xiaomi.vacuum.d109gl`).
No Xiaomi cloud account required — control happens entirely over the local
network using the MIoT protocol.

> Tested only against `xiaomi.vacuum.d109gl`. Other Xiaomi vacuums may work but
> aren't officially supported.

## Features

- **Vacuum entity** with the standard HA controls: start, pause, stop, return
  to dock, locate, fan speed, battery, state.
- **Native segment cleaning** — exposes the rooms reported by the device so
  you can use Home Assistant's *Settings → Devices & services → Entities →
  vacuum → ⚙ → Map vacuum segments to areas* dialog and call the standard
  `vacuum.clean_area` action with HA areas.
- **Configuration selects** for: cleaning mode (sweep / mop / sweep+mop /
  sweep before mopping), clean repetitions, mop water level, sweep route
  (quick / standard / deep), obstacle avoidance strategy.
- **Empty dust bin** button (triggers the dock to collect the vacuum's dust).
- **Optimistic UI updates** — actions reflect immediately in the card; a
  background refresh confirms the device state ~5 s later.
- **Internationalization**: English and Brazilian Portuguese (`pt-BR`).

## Requirements

- Home Assistant **>= 2026.4.4** (segment-to-area mapping requires the
  `VacuumEntityFeature.CLEAN_AREA` introduced in 2026.3 and the `Segment`
  dataclass).
- Python **3.14.2+**.
- Network reachability between Home Assistant and the vacuum.

## Installation

### HACS (recommended)

1. In Home Assistant, open **HACS → Integrations**.
2. Open the kebab menu (⋮) → **Custom repositories**.
3. Add `https://github.com/roquerodrigo/ha-xiaomi-vacuum` as type **Integration**.
4. Install **Xiaomi Vacuum**.
5. Restart Home Assistant.
6. **Settings → Devices & services → Add Integration → Xiaomi Vacuum**.

### Manual

1. Copy `custom_components/xiaomi_vacuum/` into your HA `config/custom_components/`
   directory.
2. Restart Home Assistant.
3. **Settings → Devices & services → Add Integration → Xiaomi Vacuum**.

## Configuration

The config flow asks for:

| Field | Required | Description |
|------|----------|-------------|
| **IP address** | yes | The vacuum's local IP (give it a DHCP reservation). |
| **MIoT token** | yes | 32-character hex token (see below). |
| **Name** | no | Friendly name for the device/entity. Defaults to the model. |

### Getting the MIoT token

The 32-char token is a per-device secret stored locally by the Mi Home app.
Two common ways to extract it without third-party services:

- **Mi Home backup**: pull the SQLite DB from the app's storage and read
  `_token` for your device.
- **[Xiaomi Cloud Tokens Extractor](https://github.com/PiotrMachowski/Xiaomi-cloud-tokens-extractor)**:
  command-line tool — note that it logs into Xiaomi Cloud just to fetch the
  token; after that, the integration itself never touches the cloud.

## Entities

| Entity | Type | Notes |
|--------|------|-------|
| `vacuum.<name>` | `vacuum` | Main control + state + segment cleaning |
| `select.<name>_mode` | `select` | Sweep / Mop / Sweep+Mop / Sweep before mopping |
| `select.<name>_clean_times` | `select` | Once / Twice |
| `select.<name>_mop_water_level` | `select` | Level 1–3 |
| `select.<name>_sweep_route` | `select` | Quick / Standard / Deep |
| `select.<name>_obstacle_avoidance` | `select` | Less collisions / High coverage |
| `button.<name>_collect_dust` | `button` | Tells the dock to empty the dust bin |

The vacuum entity exposes raw MIoT diagnostics under the `xiaomi_vacuum`
attribute key (`status_code`, `status`, `fault_code`, `cleaning_area`,
`cleaning_time`, `last_clean_time`, `mop_water_level`, `charging_state`,
`room_information_raw`).

## Example automations

Clean the kitchen every morning at 9am:

```yaml
automation:
  - alias: Morning kitchen cleanup
    trigger:
      - platform: time
        at: "09:00:00"
    action:
      - service: vacuum.clean_area
        target:
          entity_id: vacuum.aspirador
        data:
          cleaning_area_id:
            - kitchen
```

(Requires *Map vacuum segments to areas* configured first.)

## Development

```bash
scripts/setup     # install requirements (creates Python venv first if needed)
scripts/develop   # run Home Assistant in debug mode with this integration loaded
scripts/lint      # ruff format + check
.venv/bin/pytest  # tests + coverage (must stay ≥ 90%)
```

`scripts/develop` reads `.env` for `XIAOMI_VACUUM_HOST`, `XIAOMI_VACUUM_TOKEN`,
and `XIAOMI_VACUUM_NAME` to pre-fill the config flow during local dev. See
`.env.example`.

The project is based on the
[integration_blueprint](https://github.com/ludeeus/integration_blueprint)
template.

## Limitations

- **No map rendering.** The vacuum's local API only exposes map metadata
  (object names, current position, room IDs). The actual map bitmap lives in
  Xiaomi cloud storage in a proprietary binary format. Adding render support
  would require either Xiaomi cloud authentication or a parser tailored to
  the d109gl.
- The vacuum's user-friendly name set in the Mi Home app is **cloud-only** —
  the integration uses the model name (or your custom Name from setup) as
  the device name.

## License

[MIT](LICENSE)
