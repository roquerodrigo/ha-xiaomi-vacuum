# Xiaomi Vacuum

<!-- ha-marketplace:exclude-start -->
[![CI](https://github.com/roquerodrigo/ha-xiaomi-vacuum/actions/workflows/ci.yml/badge.svg)](https://github.com/roquerodrigo/ha-xiaomi-vacuum/actions/workflows/ci.yml)
[![GitHub release](https://img.shields.io/github/v/release/roquerodrigo/ha-xiaomi-vacuum)](https://github.com/roquerodrigo/ha-xiaomi-vacuum/releases/latest)
[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-db61a2?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/roquerodrigo)

[![Open your Home Assistant instance and open a repository in the Marketplace.](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=roquerodrigo&repository=ha-xiaomi-vacuum&category=integration)
<!-- ha-marketplace:exclude-end -->

Control your Xiaomi robot vacuum from Home Assistant: start and stop jobs,
clean single rooms or zones drawn on the map, change the cleaning settings and
keep an eye on brushes, filter and mop. Commands and status go straight to the
vacuum on your local network. Your Xiaomi account is used to add the vacuum
with a QR code, so there is no token to copy, and afterwards to download the
map and to show error messages in your language. The connection to the vacuum
and the map drawing come from
[xiaomi-vacuum-sdk](https://github.com/roquerodrigo/xiaomi-vacuum-sdk).

## Supported devices

| Model                       | Model ID               | Dock                                          |
|-----------------------------|------------------------|-----------------------------------------------|
| Xiaomi Robot Vacuum S20+    | `xiaomi.vacuum.b108gl` | Charging dock                                 |
| Xiaomi Robot Vacuum S40 Pro | `xiaomi.vacuum.ov71gl` | Charging dock                                 |
| Xiaomi Robot Vacuum S40C    | `xiaomi.vacuum.e101gb` | Charging dock (E101CDZ), mop tank on the robot |
| Xiaomi Robot Vacuum X20+    | `xiaomi.vacuum.c102gl` | Self-emptying dock that washes the mop        |
| Xiaomi Robot Vacuum X20 Max | `xiaomi.vacuum.d109gl` | Self-emptying dock that washes the mop        |

Other `xiaomi.vacuum.*` models can show up during setup, but they are not
supported. If you add one anyway, basic local control works and Home
Assistant shows a repair notice with a link to request support for it. To ask
for a new model, open a
[model support request](https://github.com/roquerodrigo/ha-xiaomi-vacuum/issues/new/choose).
To add it yourself, see [ADDING_A_MODEL.md](ADDING_A_MODEL.md).

### What each model supports

| Feature                                                          | S20+   | S40 Pro | S40C    | X20+    | X20 Max |
|------------------------------------------------------------------|--------|---------|---------|---------|---------|
| Start, pause, stop, return to dock, locate, fan speed            | Yes    | Yes     | Yes     | Yes     | Yes     |
| Battery, status, error and consumable life                       | Yes    | Yes     | Yes     | Yes     | Yes     |
| Mop pad and cleaning in progress                                 | Yes    | Yes     | Yes     | Yes     | Yes     |
| Room cleaning by Home Assistant area                             | Yes    | Yes     | Yes     | Yes (1) | Yes     |
| Map image                                                        | Yes    | Yes     | Yes     | Yes (2) | Yes     |
| Cleanup mode and mopping water output                            | Yes    | Yes     | Yes     | Yes (3) | Yes     |
| Cleanup times                                                    | 1 to 2 | 1 to 3  | 1 to 3  | No      | 1 to 3  |
| Cleanup path and obstacle avoidance                              | No     | Yes     | Yes     | No      | Yes     |
| Zone cleaning                                                    | No     | Yes     | Yes     | No      | Yes     |
| Custom cleanings saved in Mi Home                                | No     | No      | No      | No      | Yes     |
| Fault history from the Xiaomi cloud                              | No     | Yes     | No      | No      | Yes     |
| Empty the dust bin into the dock                                 | No     | No      | No      | Yes     | Yes     |
| Wash and dry the mop in the dock                                 | No     | No      | No      | Yes (4) | Yes     |
| Consumable hours left and reset buttons                          | No     | Yes     | Yes     | Yes     | Yes     |
| Mop drying time left and lifetime cleaning statistics            | No     | No      | No      | Yes     | No      |
| Child lock, carpet boost, cleanup resumption, do not disturb     | No     | Yes (5) | Yes (5) | Yes     | Yes     |
| Voice volume                                                     | No     | Yes (5) | Yes (5) | Yes     | Yes     |
| Carpet cleanup preference                                        | No     | Yes (5) | Yes (5) | No      | Yes     |
| Dock settings (mop washing, drying, automatic dust collection)   | No     | No      | No      | No      | Yes     |

1. The X20+ room list comes from the map in the Xiaomi cloud. Rooms you have
   not named in Mi Home are listed as "Room 1", "Room 2" and so on, as in the
   app.
2. The X20+ map shows the saved floor plan, without the robot's live position
   or its path.
3. The X20+ mopping water output has no **Off** option.
4. The X20+ dock can start washing the mop but cannot stop it.
5. Published by the S40 Pro and S40C at the same place as on the X20 Max, but
   not yet confirmed on either vacuum.

## Features

- Use the standard vacuum controls: start, pause, stop, send it back to the
  dock, make it beep and change the suction.
- Clean single rooms by Home Assistant area and, on some models, rectangles
  you draw on the map card.
- On the X20 Max, start a custom cleaning you saved in the Mi Home app by its
  name.
- See the map on your dashboard. It works with the Xiaomi Vacuum Map Card.
- Read the current fault in your language and, on some models, look back at
  recent faults.
- Know when a brush, the filter or the mop needs replacing, and reset the
  counter after you replace it.
- Change the cleaning mode, water output, route and, on the X20 Max, the dock
  settings from Home Assistant.

## Requirements

- Home Assistant 2026.4.4 or newer.
- One of the vacuums above, paired with the Mi Home app.
- The Xiaomi account the vacuum is paired with, and a phone to scan a QR code
  with.
- Home Assistant and the vacuum on the same network.

<!-- ha-marketplace:exclude-start -->
## Installation

### Home Assistant Marketplace (recommended)

1. Select the **Open your Home Assistant instance** button above, or go to
   **Settings → Marketplace**, select **Add from link** in the upper right
   corner, enter `roquerodrigo/ha-xiaomi-vacuum` and select **Add**.
2. Select **Install**.
3. Restart Home Assistant.

The Marketplace comes with Home Assistant 2026.11 and later. On older
versions, add this repository to HACS as a custom repository of type
**Integration** and install it from there.

### Manual

1. Download `xiaomi_vacuum.zip` from the
   [latest release](https://github.com/roquerodrigo/ha-xiaomi-vacuum/releases/latest).
2. Extract it into `config/custom_components/xiaomi_vacuum/`.
3. Restart Home Assistant.
<!-- ha-marketplace:exclude-end -->

## Configuration

Go to **Settings → Devices & services → Add integration** and search for
**Xiaomi Vacuum**.

1. Pick the region your Xiaomi account is registered in.

   | Field  | What to enter                                                                                                          | Default       |
   |--------|------------------------------------------------------------------------------------------------------------------------|---------------|
   | Region | The Mi Home server of your account: Europe / UK, United States, China (mainland), Russia, Singapore, India or Taiwan | United States |

   If you pick the wrong region, your vacuum is not found.
2. A QR code appears. Scan it with your phone's camera or any QR scanner app,
   not with the Mi Home app, which does not recognize it. Sign in on the
   Xiaomi page that opens. The dialog moves on by itself once you are signed
   in.
3. If your account has more than one vacuum, pick the one to add.

Home Assistant then gets the vacuum's local address and token from your
account, checks that it can reach the vacuum and adds it.

To change the region later, open the integration and select
**Reconfigure**. Your current sign-in is reused, so you do not scan a new QR
code. If Xiaomi stops accepting your sign-in, Home Assistant asks you to
reconnect and shows a new QR code. The vacuum keeps working in the meantime.

## Entities

Which entities you get depends on the model. The table in Supported devices
above shows what each model has. Entity names are also translated into
Spanish, Portuguese (Brazil), Russian and Serbian.

### Vacuum

The vacuum entity carries the device name. It shows the current state and
offers start, pause, stop, return to dock, locate and fan speed (Silent,
Standard, Strong or Turbo). Start begins a new job when the vacuum is docked
or idle, and resumes the current job otherwise.

### Sensors

| Entity                                                               | Type          | Shows                                                                     | Models                       |
|----------------------------------------------------------------------|---------------|---------------------------------------------------------------------------|------------------------------|
| Status                                                               | Sensor        | What the vacuum is doing, such as Cleaning, Cleaning mop or Returning to dock | All                      |
| Battery                                                              | Sensor        | Percentage                                                                | All                          |
| Error                                                                | Sensor        | The fault in your language, OK when there is none                         | All                          |
| Error code                                                           | Sensor        | The fault number, 0 when there is none. Diagnostic                        | All                          |
| Mop pad life, Main brush life, Side brush life, Filter life          | Sensor        | Percentage left                                                           | All                          |
| Mop pad time left, Main brush time left, Side brush time left, Filter time left | Sensor | Hours left. Diagnostic                                             | S40 Pro, S40C, X20+, X20 Max |
| Drying time left                                                     | Sensor        | Minutes of mop drying left                                                | X20+                         |
| Total cleaning time, Total cleanings, Total cleaned area             | Sensor        | Lifetime statistics. Diagnostic                                           | X20+                         |
| Charging                                                             | Binary sensor | Whether the battery is charging. Diagnostic                               | All                          |
| Mop pad                                                              | Binary sensor | Whether the mop pad is attached. Diagnostic                               | All                          |
| Cleaning in progress                                                 | Binary sensor | On for the whole job, including mop washes and recharges along the way. Diagnostic | All                 |
| Map                                                                  | Image         | The map from the Xiaomi cloud                                             | All                          |

The Error code sensor also lists every code the vacuum reports in its
attributes: `raw_fault_codes` (all of them), `active_fault_codes`,
`ignored_fault_codes` (codes the model reports for hardware it does not have)
and `fault_text`. Routine notices, such as the dust bin or water tank being
taken out, show on both error sensors without putting the vacuum in the error
state.

### Controls

Entities marked Configuration appear in the Configuration section of the
device page.

| Entity                                                     | Type   | Options                                                                     | Models                       |
|------------------------------------------------------------|--------|-----------------------------------------------------------------------------|------------------------------|
| Cleanup mode                                               | Select | Vacuuming, Mopping, Vacuuming and mopping, Vacuuming before mopping         | All                          |
| Cleanup times                                              | Select | Once, Twice, Three times (not on the S20+)                                  | S20+, S40 Pro, S40C, X20 Max |
| Mopping water output                                       | Select | Off (not on the X20+), Level 1, Level 2, Level 3. Configuration             | All                          |
| Cleanup path                                               | Select | Quick, Standard, Deep. Configuration                                        | S40 Pro, S40C, X20 Max       |
| Obstacle avoidance                                         | Select | Less collisions, High coverage. Configuration                               | S40 Pro, S40C, X20 Max       |
| Carpet cleanup preference                                  | Select | Adaptive, Avoid, Ignore, Cross. Configuration                               | S40 Pro, S40C, X20 Max       |
| Child lock, Carpet boost, Do not disturb                   | Switch | Configuration                                                               | S40 Pro, S40C, X20+, X20 Max |
| Cleanup resumption                                         | Switch | Resume an unfinished job after recharging. Configuration                    | S40 Pro, S40C, X20+, X20 Max |
| Volume                                                     | Number | 0 to 100 %. Configuration                                                   | S40 Pro, S40C, X20+, X20 Max |
| Collect dust                                               | Button | Empties the dust bin into the dock                                          | X20+, X20 Max                |
| Clean mop, Dry mop, Stop drying mop                        | Button | Washes or dries the mop in the dock                                         | X20+, X20 Max                |
| Stop cleaning mop                                          | Button | Stops washing the mop                                                       | X20 Max                      |
| Reset main brush, Reset side brush, Reset filter, Reset mop pad | Button | Resets the counter after you replace the part. Configuration         | S40 Pro, S40C, X20+, X20 Max |

Cleanup mode refuses a mopping mode while no mop pad is attached, with a
message that says so. The vacuum would otherwise ignore the change.

### X20 Max dock settings

All of these appear in the Configuration section of the device page.

| Entity                         | Type   | Options                                                    |
|--------------------------------|--------|------------------------------------------------------------|
| Auto mop cleaning              | Switch | Washes the mop at the dock during a mopping job            |
| Mop cleaning frequency         | Select | Every room, By area, By time                               |
| Mop cleaning area interval     | Select | 5, 8, 10, 15, 20 or 25 m² mopped between washes (By area)  |
| Mop cleaning time interval     | Number | 0 to 255 minutes mopped between washes (By time)           |
| Mop cleaning water output      | Select | Deep, Daily, Save water                                    |
| Mop cleaning water temperature | Select | Normal, Warm, Hot, Smart                                   |
| Drying duration                | Select | 2 hours, 3 hours, 4 hours                                  |
| Auto mop drying                | Switch | Dries the mop at the dock after each job                   |
| Automatic dust collection      | Switch | Empties the dust bin into the dock after a job             |
| Dust collection frequency      | Select | Every job, Every 2 jobs, Every 3 jobs                      |

## Actions

### Clean rooms

Open the vacuum entity's settings in Home Assistant and match each room the
vacuum reports to one of your areas. Then use the standard
`vacuum.clean_area` action. For example, to clean the kitchen every morning:

```yaml
automation:
  - alias: Morning kitchen cleanup
    triggers:
      - trigger: time
        at: "09:00:00"
    actions:
      - action: vacuum.clean_area
        target:
          entity_id: vacuum.robot_vacuum
        data:
          cleaning_area_id:
            - kitchen
```

### Clean zone (`xiaomi_vacuum.clean_zone`)

Cleans one or more rectangles on the S40 Pro, S40C and X20 Max.

| Field   | Required | What it takes                                                                                   |
|---------|----------|-------------------------------------------------------------------------------------------------|
| Zones   | Yes      | A list of rectangles, each as two opposite corners `[x1, y1, x2, y2]` in millimetres on the vacuum's map |
| Repeats | No       | How many times each zone is cleaned, from 1 to 3. Also changes the Cleanup times setting. Without it, the current setting is used |

```yaml
action: xiaomi_vacuum.clean_zone
target:
  entity_id: vacuum.robot_vacuum
data:
  zones:
    - [260, 250, 890, 750]
  repeats: 1
```

The easiest way to get the coordinates is to draw the rectangle on the map
card. See Dashboard card below.

### Start custom cleaning (`xiaomi_vacuum.start_custom_cleaning`)

Starts a custom cleaning saved in the Mi Home app, with the rooms or zones and
the settings stored in it. Available on the X20 Max.

| Field | Required | What it takes                                                    |
|-------|----------|------------------------------------------------------------------|
| Name  | Yes      | The name of the custom cleaning as shown in Mi Home. Case is ignored |

```yaml
action: xiaomi_vacuum.start_custom_cleaning
target:
  entity_id: vacuum.robot_vacuum
data:
  name: Afternoon cleaning
```

In the action editor, the name field lists the custom cleanings the vacuum
reports. You can also type a name that is not listed yet, for example one you
added in the app a moment ago. An unknown name fails with the list of
cleanings the vacuum has.

### Refresh fault history (`xiaomi_vacuum.refresh_fault_history`)

Reads up to 50 recent faults from the Xiaomi cloud and returns them in the
action response. It does not mark the notifications as read in the Mi Home
app. Available on the S40 Pro and X20 Max, and it needs the Xiaomi cloud
connection.

```yaml
- action: xiaomi_vacuum.refresh_fault_history
  target:
    entity_id: vacuum.robot_vacuum
  response_variable: fault_history
```

The response is grouped by vacuum. Each fault has its code and, when Xiaomi
provides them, the text and a Unix timestamp:

```yaml
vacuum.robot_vacuum:
  fault_history:
    - code: 100025
      text: "Insufficient water"
      timestamp: 1794441000
```

Xiaomi decides how long faults stay available, so this is not a permanent
archive.

### Extra commands (`vacuum.send_command`)

These commands take no parameters.

| Command                                          | What it does                          | Models                       |
|--------------------------------------------------|---------------------------------------|------------------------------|
| `continue_sweep`                                 | Resumes a paused job                  | All                          |
| `start_only_sweep`, `start_mop`, `start_sweep_mop` | Starts a job that vacuums, mops, or does both | S20+, S40 Pro, S40C, X20 Max |
| `start_mop_wash`, `start_dry`, `stop_dry`        | Washes the mop, starts or stops drying it | X20+, X20 Max            |
| `stop_mop_wash`                                  | Stops washing the mop                 | X20 Max                      |

```yaml
action: vacuum.send_command
target:
  entity_id: vacuum.robot_vacuum
data:
  command: start_dry
```

## Dashboard card

This integration has no card of its own. The Map entity works with the
[Xiaomi Vacuum Map Card](https://github.com/PiotrMachowski/lovelace-xiaomi-vacuum-map-card):
it carries the `calibration_points` the card needs to place the map. The
card's own drawing modes call services of other integrations and do not work
here. On the S40 Pro, S40C and X20 Max, add this map mode to draw zones and
clean them:

```yaml
type: custom:xiaomi-vacuum-map-card
entity: vacuum.robot_vacuum
map_source:
  camera: image.robot_vacuum_map
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

On the S20+ and X20+, which have no zone cleaning, set `map_modes: []` and
clean rooms with `vacuum.clean_area`.

The Map entity also has a `calibration` attribute with the raw map geometry,
for other cards.

## How it works

Home Assistant reads the vacuum's state over your local network every 30
seconds. When you send a command, the change shows right away and Home
Assistant checks the vacuum again about 5 seconds later.

The map is downloaded from the Xiaomi cloud every 60 seconds and kept across
restarts, so it still shows while the vacuum is offline. The text of a new
fault is also read from the Xiaomi cloud, in the language of your Xiaomi
account. On the S20+, room cleaning goes through the Xiaomi cloud, which is
more reliable for that command, and falls back to the local network if the
cloud is not available.

The Xiaomi sign-in expires after a few weeks. Home Assistant renews it on its
own and only asks you to scan a new QR code when Xiaomi refuses to renew it.

## Troubleshooting

**Setup says no vacuum was found in my account.** The region must be the one
your Mi Home account uses. Start again and pick another region. The S40 Pro
is not available in the China (mainland) region.

**The Mi Home app does not open the QR code.** Scan it with the phone's
camera or a QR scanner app instead.

**Setup says Home Assistant cannot reach the vacuum.** Make sure the vacuum is
on and connected to the same network as Home Assistant, then try again.

**The vacuum shows as unavailable and there is a "Cannot reach" repair.** The
vacuum is off or lost its network connection. The repair goes away by itself
once it is back.

**A repair says my vacuum is an unsupported model.** Your model is not in the
list above. Local control keeps working, but some entities can be wrong or
missing. Use the link in the repair to request support. The model is already
filled in.

**The map stopped updating.** Home Assistant could not renew the Xiaomi
sign-in. Open the reconnect notice under **Settings → Devices & services** and
scan the new QR code.

**Selecting a mopping mode fails.** Attach the mop pad and try again.

**Something else is wrong.** Download the diagnostics from the integration's
menu and attach them to an
[issue](https://github.com/roquerodrigo/ha-xiaomi-vacuum/issues). The token
and the Xiaomi sign-in are removed from the file.

## Known limitations

- The map, the error text, the X20+ room list and the fault history need the
  Xiaomi cloud. Starting, stopping and the settings work without it.
- Spot cleaning and manual driving are not available.
- The X20+ map does not show where the robot is right now.

## Support

This integration is built and maintained on personal time, on hardware bought
for the purpose. If it is useful to you, consider
[sponsoring the work](https://github.com/sponsors/roquerodrigo). It keeps the
devices, the testing and the releases coming.

<!-- ha-marketplace:exclude-start -->
## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup and
workflow, and [CODE_STYLE.md](CODE_STYLE.md) for the code conventions.

## License

[MIT](LICENSE)
<!-- ha-marketplace:exclude-end -->
