# Xiaomi Vacuum for Home Assistant

[![CI](https://github.com/roquerodrigo/ha-xiaomi-vacuum/actions/workflows/ci.yml/badge.svg)](https://github.com/roquerodrigo/ha-xiaomi-vacuum/actions/workflows/ci.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

[![Open your Home Assistant instance and open the repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=roquerodrigo&repository=ha-xiaomi-vacuum&category=integration)

---

A [Home Assistant](https://www.home-assistant.io/) integration for the
**Xiaomi Robot Vacuum X20 Max** (`xiaomi.vacuum.d109gl`) and **Xiaomi Robot
Vacuum S20+** (`xiaomi.vacuum.b108gl`).

Day-to-day control and state polling run **locally** over the MIoT protocol
(`iot_class: local_polling`). The Xiaomi cloud is used for one-time setup —
a QR login that discovers the vacuum and fetches its IP and token for you — and
for two cloud-only extras: the **map image** and **localized error messages**.

> Tested against `xiaomi.vacuum.d109gl` (X20 Max) and `xiaomi.vacuum.b108gl`
> (S20+). Other Xiaomi vacuums matching the `xiaomi.vacuum.*` model prefix may
> be discovered but aren't officially supported.

## Features

- **Vacuum entity** with the standard HA controls: start, pause, stop, return
  to dock, locate, fan speed, battery, state.
- **Native segment cleaning** — exposes the rooms reported by the device so
  you can use Home Assistant's *Settings → Devices & services → Entities →
  vacuum → ⚙ → Map vacuum segments to areas* dialog and call the standard
  `vacuum.clean_area` action with HA areas.
- **Map image** — the live map is rendered from the Xiaomi cloud as an `image`
  entity you can drop on a dashboard.
- **Error reporting** — `Error` (localized, human-readable fault text resolved
  from the Xiaomi cloud message feed) and `Error code` sensors. The fault is
  read from the device's *live* fault list, so it clears once the vacuum
  recovers.
- **Consumable life sensors** (% remaining): mop, main brush, side brush,
  filter — matching the Mi Home app's consumables list.
- **Configuration selects** for: cleaning mode (sweep / mop / sweep+mop /
  sweep before mopping), clean repetitions, mop water level. The X20 Max also
  exposes sweep route (quick / standard / deep) and obstacle avoidance
  strategy; the S20+ has no such properties and omits those selects.
- **Empty dust bin** button (triggers the dock to collect the vacuum's dust).
- **`vacuum.send_command`** — a whitelist of extra MIoT actions (start mop,
  sweep+mop, continue sweep; and on the X20 Max, mop wash start/stop and dry
  start/stop). The mop-wash and dry actions target the X20 Max auto-wash dock
  and are not available on the S20+.
- **Optimistic UI updates** — actions reflect immediately in the card; a
  background refresh confirms the device state ~5 s later.
- **Internationalization**: English and Brazilian Portuguese (`pt-BR`).

## Requirements

- Home Assistant **>= 2026.4.4** (segment-to-area mapping requires the
  `VacuumEntityFeature.CLEAN_AREA` introduced in 2026.3 and the `Segment`
  dataclass).
- Python **3.14.2+**.
- A **Xiaomi account** — used during setup (QR login) and, afterwards, only to
  fetch the map and the localized error text. Control and state stay local.
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

Setup is cloud-assisted — there is **no token to copy by hand**:

1. **Settings → Devices & services → Add Integration → Xiaomi Vacuum**.
2. Pick the **Xiaomi cloud region** your Mi Home account is registered in
   (Europe and the UK use the Germany server).
3. A **QR code** appears. Open the **Mi Home** app and scan it to authorize the
   login to your Xiaomi account.
4. The integration lists the vacuums on the account and lets you pick one (it
   auto-selects if there's only one).
5. It pulls the device's **local IP and token** from the cloud, verifies the
   local connection, and creates the entry.

The cloud session captured during this flow (service token, user id) is stored
with the config entry and reused to render the map, resolve localized error
text, and route the S20+ room clean through the cloud.

> Picked the wrong region, or your vacuum was not found? Open the entry's
> **Reconfigure** option to switch the cloud region without re-adding the
> integration.

## Entities

| Entity | Type | Notes |
|--------|------|-------|
| `vacuum.<name>` | `vacuum` | Main control + state + segment cleaning + `send_command` |
| `image.<name>_map` | `image` | Map rendered from the Xiaomi cloud |
| `sensor.<name>_battery` | `sensor` | Battery level |
| `sensor.<name>_error` | `sensor` | Localized fault text (`OK` when healthy) |
| `sensor.<name>_error_code` | `sensor` | Raw fault code (`0` when healthy) |
| `sensor.<name>_mop_life` | `sensor` | Mop remaining life (%) |
| `sensor.<name>_main_brush_life` | `sensor` | Main brush remaining life (%) |
| `sensor.<name>_side_brush_life` | `sensor` | Side brush remaining life (%) |
| `sensor.<name>_filter_life` | `sensor` | Filter remaining life (%) |
| `select.<name>_mode` | `select` | Sweep / Mop / Sweep+Mop / Sweep before mopping |
| `select.<name>_clean_times` | `select` | Once / Twice (X20 Max also: Three times) |
| `select.<name>_mop_water_level` | `select` | Off (S20+ only) / Level 1–3 |
| `select.<name>_sweep_route` | `select` | Quick / Standard / Deep — X20 Max only |
| `select.<name>_obstacle_avoidance` | `select` | Less collisions / High coverage — X20 Max only |
| `button.<name>_collect_dust` | `button` | Tells the dock to empty the dust bin — X20 Max only |

The vacuum entity also exposes raw MIoT diagnostics as extra state attributes
under the `xiaomi_vacuum` key.

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
uv run ruff format .                          # format
uv run ruff check . --fix                      # lint + autofix
uv run mypy custom_components/xiaomi_vacuum    # type-check
uv run pytest                                  # tests + coverage (must stay ≥ 90%)
```

The project is based on the
[integration_blueprint](https://github.com/ludeeus/integration_blueprint)
template.

## Limitations

- The **map** and **localized error text** depend on the Xiaomi cloud session
  captured at setup. When that session expires, Home Assistant raises a
  **re-authentication prompt** — scan a fresh QR code and everything resumes;
  local control keeps working in the meantime.

## License

[MIT](LICENSE)
