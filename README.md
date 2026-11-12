# Xiaomi Vacuum for Home Assistant

[![CI](https://github.com/roquerodrigo/ha-xiaomi-vacuum/actions/workflows/ci.yml/badge.svg)](https://github.com/roquerodrigo/ha-xiaomi-vacuum/actions/workflows/ci.yml)
[![Home Assistant Marketplace](https://img.shields.io/badge/Home%20Assistant%20Marketplace-Custom-orange.svg)](https://www.home-assistant.io/integrations/marketplace/)

[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-db61a2?logo=githubsponsors&logoColor=white&style=for-the-badge)](https://github.com/sponsors/roquerodrigo)

[![Open your Home Assistant instance and open the repository in the Home Assistant Marketplace.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=roquerodrigo&repository=ha-xiaomi-vacuum&category=integration)

---

A [Home Assistant](https://www.home-assistant.io/) integration for Xiaomi
robot vacuums. Day-to-day control and state polling run **locally** over the
MIoT protocol (`iot_class: local_polling`). The Xiaomi cloud is used for the
one-time setup — a QR login that finds the vacuum and fetches its IP and token
for you — and for the **map image** and the **localized error messages**.

## Supported models

| Model | Model ID | Notes |
|-------|----------|-------|
| Xiaomi Robot Vacuum S20+ | `xiaomi.vacuum.b108gl` | Plain charging dock |
| Xiaomi Robot Vacuum S40 Pro | `xiaomi.vacuum.ov71gl` | Plain charging dock; export-only, so it is not listed when the cloud region is set to China |
| Xiaomi Robot Vacuum X20+ | `xiaomi.vacuum.c102gl` | Built by Dreame with its own MIoT layout; self-emptying, mop-washing dock |
| Xiaomi Robot Vacuum X20 Max | `xiaomi.vacuum.d109gl` | Self-emptying, mop-washing dock |

Other vacuums matching the `xiaomi.vacuum.*` model prefix may be discovered,
but they are not supported. To request a new model, open a
[model support issue](https://github.com/roquerodrigo/ha-xiaomi-vacuum/issues/new/choose);
to add one yourself, see [`ADDING_A_MODEL.md`](ADDING_A_MODEL.md).

### What each model supports

| Feature | S20+ | S40 Pro | X20+ | X20 Max |
|---------|:----:|:-------:|:----:|:-------:|
| Start, pause, stop, return to dock, locate, fan speed | ✅ | ✅ | ✅ | ✅ |
| Battery, status, error and consumable life sensors | ✅ | ✅ | ✅ | ✅ |
| Mop pad and cleaning-in-progress sensors | ✅ | ✅ | ✅ | ✅ |
| Room cleaning with Home Assistant areas | ✅ | ✅ | ✅ ¹ | ✅ |
| Map image | ✅ | ✅ | ✅ ² | ✅ |
| Cleaning mode and mop water level selects | ✅ | ✅ | ✅ ³ | ✅ |
| Clean repetitions select | 1–2 | 1–3 | — | 1–3 |
| Sweep route and obstacle avoidance selects | — | ✅ | — | ✅ |
| Zone cleaning (`xiaomi_vacuum.clean_zone`) | — | ✅ ⁵ | — | ✅ |
| Custom cleanings (`xiaomi_vacuum.start_custom_cleaning`) | — | — | — | ✅ |
| Empty the dust bin into the dock | — | — | ✅ | ✅ |
| Wash and dry the mop in the dock | — | — | ✅ ⁴ | ✅ |
| Consumable hours left and reset buttons | — | ✅ | ✅ | ✅ |
| Mop drying time left and lifetime cleaning statistics | — | — | ✅ | — |
| Child lock, carpet boost, resume after charging, do not disturb | — | — | ✅ | — |
| Voice volume | — | — | ✅ | — |

1. The X20+ room list is read from the cloud map. Rooms left unnamed in Mi
   Home are listed as "Room N", as in the app.
2. The X20+ map shows the saved floor plan and the dock, without the live robot
   position or path.
3. The X20+ mop water level has no *Off* option.
4. The X20+ dock can start washing the mop but not stop it.
5. The S40 Pro uses the X20 Max rectangle command path. Real-device user
   testing on 10 November 2026 confirmed that the S40 Pro cleaned 20 selected
   rectangles in response to the zone-cleaning command.

## Features

- **Vacuum entity** with the standard Home Assistant controls: start, pause,
  stop, return to dock, locate, fan speed, battery and state.
- **Room cleaning** — the rooms the vacuum reports can be mapped to Home
  Assistant areas in *Settings → Devices & services → Entities → vacuum → ⚙ →
  Map vacuum segments to areas*, and then cleaned with the standard
  `vacuum.clean_area` action.
- **Zone cleaning** — the `xiaomi_vacuum.clean_zone` action cleans one or more
  rectangles in the vacuum's map coordinates. See
  [Using the map with the Xiaomi Vacuum Map Card](#using-the-map-with-the-xiaomi-vacuum-map-card).
- **Custom cleanings** — the `xiaomi_vacuum.start_custom_cleaning` action
  starts a custom cleaning saved in the Mi Home app by its name. See
  [Starting a custom cleaning](#starting-a-custom-cleaning).
- **Map image** — the map is rendered from the Xiaomi cloud as an `image`
  entity, with the calibration the Xiaomi Vacuum Map Card needs.
- **Error reporting** — a localized, human-readable fault text and the raw
  fault code. The fault is read from the vacuum's live fault list, so it clears
  once the vacuum recovers. Routine notices (dust bin or water tank taken out)
  show on these sensors without switching the vacuum entity to `error`.
- **Optimistic updates** — actions are reflected right away, and a background
  refresh confirms the vacuum's state about 5 seconds later.

## Requirements

- Home Assistant **2026.4.4** or newer.
- A **Xiaomi account** — used during setup (QR login) and, afterwards, only to
  fetch the map and the localized error text. Control and state stay local.
- Network reachability between Home Assistant and the vacuum.

## Installation

### Home Assistant Marketplace (recommended)

1. Open **Settings → Marketplace**, or select the *Open your Home Assistant
   instance* button above.
2. Select **Add from link** in the upper-right corner, enter
   `roquerodrigo/ha-xiaomi-vacuum` and select **Add**.
3. Install **Xiaomi Vacuum**.
4. Restart Home Assistant.
5. Add the integration, as described in [Configuration](#configuration).

The Marketplace is built into Home Assistant from 2026.11. On older versions,
add the repository as a custom repository of type **Integration** in HACS
instead.

### Manual

1. Copy `custom_components/xiaomi_vacuum/` into the
   `config/custom_components/` directory of your Home Assistant.
2. Restart Home Assistant.
3. Add the integration, as described in [Configuration](#configuration).

## Configuration

Setup is cloud-assisted, so there is **no token to copy by hand**:

1. Open **Settings → Devices & services → Add Integration → Xiaomi Vacuum**.
2. Pick the **Xiaomi cloud region** your Mi Home account is registered in
   (Europe and the UK use the Germany server).
3. A **QR code** appears. Scan it with your **phone camera** or any QR scanner
   app — **not** the Mi Home app, which does not recognize it — and sign in on
   the Xiaomi page that opens.
4. Pick the vacuum from the list of vacuums on the account (it is selected
   automatically when there is only one).
5. The integration fetches the vacuum's **local IP and token** from the cloud,
   checks the local connection and creates the entry.

The cloud session from this flow is stored with the entry and reused to render
the map, resolve the localized error text, read the X20+ room list and start
room cleaning on the S20+.

> Picked the wrong region, or the vacuum was not found? Use the entry's
> **Reconfigure** option to switch the cloud region without removing the
> integration.

## Entities

Entity IDs follow the Home Assistant language at the time the entry is added;
the English names are shown below.

| Entity | Models | Notes |
|--------|--------|-------|
| `vacuum.<name>` | All | Main control, state, room cleaning and `send_command` |
| `image.<name>_map` | All | Map rendered from the Xiaomi cloud |
| `sensor.<name>_status` | All | Detailed status (Idle, Charging, Sweeping, …) |
| `sensor.<name>_battery` | All | Battery level |
| `sensor.<name>_error` | All | Localized fault text (`OK` when healthy) |
| `sensor.<name>_error_code` | All | Raw fault code (`0` when healthy) |
| `sensor.<name>_mop_life`, `_main_brush_life`, `_side_brush_life`, `_filter_life` | All | Consumable life left (%) |
| `sensor.<name>_mop_time_left`, `_main_brush_time_left`, `_side_brush_time_left`, `_filter_time_left` | S40 Pro, X20+, X20 Max | Consumable hours left |
| `sensor.<name>_drying_time_left` | X20+ | Minutes of mop drying left |
| `sensor.<name>_total_cleaning_time`, `_total_cleanings`, `_total_cleaned_area` | X20+ | Lifetime cleaning statistics |
| `binary_sensor.<name>_charging` | All | Whether the battery is charging |
| `binary_sensor.<name>_mop_pad` | All | Whether the mop pad is attached |
| `binary_sensor.<name>_cleaning_in_progress` | All | Whether a cleaning job is underway, including mop washes and recharges in the middle of a job |
| `select.<name>_mode` | All | Sweep, Mop, Sweep and mop, Sweep before mopping |
| `select.<name>_mop_water_level` | All | Off (except X20+), Level 1–3 |
| `select.<name>_clean_times` | S20+, S40 Pro, X20 Max | Once, Twice, Three times (not on the S20+) |
| `select.<name>_sweep_route` | S40 Pro, X20 Max | Quick, Standard, Deep |
| `select.<name>_obstacle_avoidance` | S40 Pro, X20 Max | Less collisions, High coverage |
| `button.<name>_collect_dust` | X20+, X20 Max | Empties the dust bin into the dock |
| `button.<name>_wash_mop`, `_dry_mop`, `_stop_drying_mop` | X20+, X20 Max | Washes or dries the mop in the dock |
| `button.<name>_stop_washing_mop` | X20 Max | Stops washing the mop |
| `button.<name>_reset_main_brush`, `_reset_side_brush`, `_reset_filter`, `_reset_mop` | S40 Pro, X20+, X20 Max | Resets a consumable after replacing it |
| `switch.<name>_child_lock`, `_carpet_boost`, `_resume_after_charging`, `_do_not_disturb` | X20+ | Device settings |
| `number.<name>_volume` | X20+ | Voice volume, 0–100 % |

The vacuum entity also exposes raw MIoT diagnostics as extra state attributes
under the `xiaomi_vacuum` key.

Selecting a mop mode while no mop pad is attached is refused with a clear
error: the vacuum itself silently reverts such a change, so the integration
reports the reason instead of letting the select snap back.

## Actions

### Sending extra commands

`vacuum.send_command` accepts these commands, without parameters:

| Command | Models |
|---------|--------|
| `continue_sweep` | All |
| `start_only_sweep`, `start_mop`, `start_sweep_mop` | S20+, S40 Pro, X20 Max |
| `start_mop_wash`, `start_dry`, `stop_dry` | X20+, X20 Max |
| `stop_mop_wash` | X20 Max |

```yaml
action: vacuum.send_command
target:
  entity_id: vacuum.<name>
data:
  command: start_dry
```

### Starting a custom cleaning

Custom cleanings are created in the Mi Home app, each with its own rooms or
zones and cleaning settings. On the X20 Max, the
`xiaomi_vacuum.start_custom_cleaning` action starts one by its name, matched
without regard to case:

```yaml
action: xiaomi_vacuum.start_custom_cleaning
target:
  entity_id: vacuum.<name>
data:
  name: Afternoon cleaning
```

In the action editor, the name field is a dropdown with the custom cleanings
the vacuum reports when the integration loads and after each call. A name that
is not listed yet can still be typed: the list is read from the vacuum on every
call, so cleanings added or renamed in the app work right away. An unknown name
fails with the list of cleanings the vacuum reports.

### Cleaning zones

On the X20 Max and S40 Pro, the `xiaomi_vacuum.clean_zone` action sends one or more
rectangles, each given as two opposite corners `[x1, y1, x2, y2]` in the
vacuum's millimetre coordinates, with an optional number of repeats:

```yaml
action: xiaomi_vacuum.clean_zone
target:
  entity_id: vacuum.<name>
data:
  zones:
    - [260, 250, 890, 750]
  repeats: 1
```

### Using the map with the Xiaomi Vacuum Map Card

The map image entity carries a `calibration_points` attribute that maps the
pixels of the served PNG to the vacuum's millimetre coordinates, in the format
the [Xiaomi Vacuum Map Card](https://github.com/PiotrMachowski/lovelace-xiaomi-vacuum-map-card)
reads. The card resolves its map source through the entity's `entity_picture`,
so the `image` entity can be used directly.

The card's built-in interactive modes call other integrations' services and do
not work here. On the X20 Max and S40 Pro, a custom map mode drives zone cleaning instead:

```yaml
type: custom:xiaomi-vacuum-map-card
entity: vacuum.<name>
map_source:
  camera: image.<name>_map
calibration_source:
  camera: true
vacuum_platform: default
map_modes:
  - name: Zone cleaning
    icon: mdi:selection-drag
    selection_type: MANUAL_RECTANGLE
    max_selections: 5
    repeats_type: EXTERNAL
    max_repeats: 3
    service_call_schema:
      service: xiaomi_vacuum.clean_zone
      service_data:
        zones: "[[selection]]"
        repeats: "[[repeats]]"
      target:
        entity_id: "[[entity_id]]"
```

On the S20+ and X20+, set `map_modes: []`, since zone cleaning is not
available, and use the `vacuum.clean_area` action for rooms.

The raw geometry (`origin_x`, `origin_y`, `resolution`, `width`, `height`,
`scale`, `border`) is also exposed as a `calibration` attribute for other
consumers.

## Example automation

Clean the kitchen every morning at 9am, once *Map vacuum segments to areas* is
configured:

```yaml
automation:
  - alias: Morning kitchen cleanup
    triggers:
      - trigger: time
        at: "09:00:00"
    actions:
      - action: vacuum.clean_area
        target:
          entity_id: vacuum.<name>
        data:
          cleaning_area_id:
            - kitchen
```

## Limitations

- The **map**, the **localized error text** and the **X20+ room list** depend
  on the Xiaomi cloud session from setup. When that session expires, Home
  Assistant asks you to **re-authenticate**: scan a fresh QR code and
  everything resumes. Local control keeps working in the meantime.

## Development

```bash
uv sync                                        # install the dependencies into .venv
scripts/develop                                # run Home Assistant with this integration loaded
uv run ruff format .                           # format
uv run ruff check . --fix                      # lint with autofix
uv run mypy custom_components/xiaomi_vacuum    # type-check
uv run pytest                                  # tests with coverage (must stay at 90 % or more)
```

Contribution guidelines are in [`CONTRIBUTING.md`](CONTRIBUTING.md) and the
code conventions in [`CODE_STYLE.md`](CODE_STYLE.md). The project is based on
the [integration_blueprint](https://github.com/ludeeus/integration_blueprint)
template.

## Support

This integration is built and maintained on personal time, on hardware bought for the purpose. If it is useful to you, consider [sponsoring the work](https://github.com/sponsors/roquerodrigo) — it keeps the devices, the testing and the releases coming.

## License

[MIT](LICENSE)


### Xiaomi fault diagnostics (development)

The `error_code` diagnostic sensor retains its numeric state and exposes
`active_fault_codes`, `raw_fault_codes`, `ignored_fault_codes` and
`cloud_fault_history` (on-demand and held in memory only).

To refresh fault history without marking Xiaomi notifications as read:

```yaml
action: xiaomi_vacuum.refresh_fault_history
target:
  entity_id: vacuum.your_xiaomi_vacuum
```

An active Xiaomi cloud session is required. Xiaomi determines which historical
fault messages remain available; this is not a permanent event archive.
