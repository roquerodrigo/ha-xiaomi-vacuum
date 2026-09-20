# Xiaomi Home — Vacuum Control API

How the Xiaomi Home app controls vacuums via the **miot-spec** protocol, the cloud
transport, and the **complete spec for `xiaomi.vacuum.d109gl`** (this integration's
historical target model). The S20+ (`xiaomi.vacuum.b108gl`) is also supported;
its divergences are summarised in `custom_components/xiaomi_vacuum/spec/`.
All identifiers below come from the public miot-spec service.

---

## 1. Where the spec comes from

There is no per-model spec hardcoded anywhere — a device's capabilities are published as a
miot-spec instance, keyed by its `urn`, on the public service:

- `https://miot-spec.org/miot-spec-v2/instances?status=all` — find the `urn` for a model
- `https://miot-spec.org/miot-spec-v2/instance?type=<urn>` — full spec (all SIID/PIID/AIID)

This is the authoritative source for the identifiers. To extend the integration, query
`miot-spec.org` directly.

`xiaomi.vacuum.d109gl` has two released spec versions; **v2** is current:
`urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-d109gl:2`

---

## 2. Cloud transport

Base host:

| Region           | Host                                                                  |
|------------------|-----------------------------------------------------------------------|
| China (mainland) | `https://api.io.mi.com/app`                                           |
| Other regions    | `https://{region}.api.io.mi.com/app` (region ∈ de, us, sg, ru, i2, …) |

This matches `XiaomiCloud._api_url()` in `custom_components/.../cloud.py` (`f"https://{prefix}api.io.mi.com/app"`).

All control calls are `POST`, body field `data=<json>`, **RC4-encrypted** with a signed
nonce (your `cloud.py` already implements `_gen_enc_params` / `_enc_signature`).

### Endpoints

| Endpoint                                       | Purpose                                  |
|------------------------------------------------|------------------------------------------|
| `/miotspec/prop/get`                           | Read properties (SIID/PIID)              |
| `/miotspec/prop/set`                           | Write properties (SIID/PIID)             |
| `/miotspec/action`                             | Invoke an action (SIID/AIID)             |
| `/miotspec/event/get`                          | Read events                              |
| `/home/device_list`                            | Enumerate devices (did, model, token, …) |
| `/home/rpc/`, `/home/rpcv2/`, `/home/batchrpc` | Legacy miio JSON-RPC (older devices)     |

---

## 3. miot-spec request/response formats

### Action — `POST /miotspec/action`

```json
{
  "params": {
    "did": "<did>",
    "siid": 2,
    "aiid": 1,
    "in": [
      /* args */
    ]
  }
}
```

Response: `{ "did", "siid", "aiid", "code": 0, "out": [ ... ] }` (`code` 0 = success)

### Property set — `POST /miotspec/prop/set`

```json
{
  "params": [
    {
      "did": "<did>",
      "siid": 2,
      "piid": 4,
      "value": 3
    }
  ]
}
```

Response: `{ "code": 0, "result": [ { "did", "siid", "piid", "code" } ] }`
(per-item `code` 0 or 1 = success)

### Property get — `POST /miotspec/prop/get`

```json
{
  "params": [
    {
      "did": "<did>",
      "siid": 2,
      "piid": 2
    }
  ]
}
```

Response: `{ "code": 0, "result": [ { "did", "siid", "piid", "value", "code" } ] }`

`miid` is optional (multi-instance / sub-devices only). Local control (LAN "OTU" hub) uses
the same payloads with methods `get_properties` / `set_properties` / `action`.

---

## 4. Complete spec — `xiaomi.vacuum.d109gl` (v2)

Legend: access `r`=read `w`=write `n`=notify. Rows already wired into this integration are
marked **✓** (verified correct against the spec).

### SIID 2 — Robot Cleaner (the main service)

**Properties**

| piid | name                            | format | access | values / range                                                                                                                                                                                                                                                                                                        | mapped |
|------|---------------------------------|--------|--------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|
| 1    | Vacuum Firmware Version         | string | r,n    |                                                                                                                                                                                                                                                                                                                       |        |
| 2    | **Status**                      | uint8  | r,n    | 1 Idle, 2 Charging, 3 BreakCharging, 4 Sweeping, 5 Paused, 6 GoCharging, 7 GoWash, 8 Remote, 9 Charged, 10 BuildingMap, 11 Updating, 12 MultiTaskStationWorking, 13 MultiTaskRecharge, 14 StationWorking, 15 Error, 16 Sweep+Mop, 17 Mopping, 18 MappingPause, 19 GoChargeBreak, 20 WashBreak, 21 GoChargeBuildingMap | ✓      |
| 3    | Device Fault                    | uint32 | r,n    | 0–420000 — latches the last code and never resets; deliberately NOT mapped                                                                                                                                                                                                                                            |        |
| 4    | **Sweep Mop Type**              | uint8  | r,w,n  | 1 Sweep, 2 Mop, 3 Sweep Mop, 4 Sweep Before Mopping                                                                                                                                                                                                                                                                   | ✓      |
| 5    | Sweep Type                      | uint8  | r,w,n  | 1 Global, 2 Zone, 3 Area, 4 Edge, 5 Custom, 6 Point, 7 Custom Area                                                                                                                                                                                                                                                    |        |
| 6    | **Cleaning Area**               | uint32 | r,n    | (m²)                                                                                                                                                                                                                                                                                                                  | ✓      |
| 7    | **Cleaning Time**               | uint32 | r,n    | seconds                                                                                                                                                                                                                                                                                                               | ✓      |
| 8    | **Clean Times**                 | uint8  | r,w,n  | 1 One, 2 Two, 3 Three                                                                                                                                                                                                                                                                                                 | ✓      |
| 9    | **Mode** (fan speed)            | uint8  | r,w,n  | 1 Silent, 2 Basic, 3 Strong, 4 Full Speed                                                                                                                                                                                                                                                                             | ✓      |
| 10   | **Mop Water Output Level**      | uint8  | r,w,n  | 0 Off, 1 L1, 2 L2, 3 L3                                                                                                                                                                                                                                                                                                | ✓      |
| 11   | Mop Status                      | bool   | r,n    | mop pad attached                                                                                                                                                                                                                                                                                                      |        |
| 12   | Zone IDs                        | string | r,n    | (used by aiid 12/37)                                                                                                                                                                                                                                                                                                  |        |
| 13   | Restricted Sweep Areas          | string | r,w,n  |                                                                                                                                                                                                                                                                                                                       |        |
| 14   | Restricted Walls                | string | r,w,n  |                                                                                                                                                                                                                                                                                                                       |        |
| 15   | Vacuum Room IDs                 | string | —      | (input to aiid 11/16)                                                                                                                                                                                                                                                                                                 |        |
| 16   | **Room Information**            | string | r,n    |                                                                                                                                                                                                                                                                                                                       | ✓      |
| 17   | **Last Clean Time**             | uint32 | r,n    |                                                                                                                                                                                                                                                                                                                       | ✓      |
| 18   | Base Station Working Status     | string | r,n    |                                                                                                                                                                                                                                                                                                                       |        |
| 19   | Order Clean                     | string | r,n    | scheduled cleans                                                                                                                                                                                                                                                                                                      |        |
| 20   | Carpet Boost                    | bool   | r,w,n  |                                                                                                                                                                                                                                                                                                                       |        |
| 21   | Carpet Avoidance                | bool   | r,w,n  |                                                                                                                                                                                                                                                                                                                       |        |
| 22   | Carpet Display                  | bool   | r,w,n  |                                                                                                                                                                                                                                                                                                                       |        |
| 23   | Sweep Break Switch              | bool   | r,w,n  | resume after charge                                                                                                                                                                                                                                                                                                   |        |
| 25   | Sleep Status                    | bool   | r,n    |                                                                                                                                                                                                                                                                                                                       |        |
| 26   | Location Status                 | bool   | r,n    |                                                                                                                                                                                                                                                                                                                       |        |
| 28   | Enable Mop Wash                 | bool   | r,w,n  |                                                                                                                                                                                                                                                                                                                       |        |
| 29   | Frequency Mop Wash              | uint8  | r,w,n  | 0 By Room, 1 By Area, 2 By Time                                                                                                                                                                                                                                                                                       |        |
| 30   | Water Output For Washing Mop    | uint8  | r,w,n  | 0 Deep, 1 Daily, 2 Save Water                                                                                                                                                                                                                                                                                         |        |
| 31   | Drying Time                     | uint8  | r,w,n  | 1 2h, 2 3h, 3 4h                                                                                                                                                                                                                                                                                                      |        |
| 32   | Auto Dust Arrest                | bool   | r,w,n  |                                                                                                                                                                                                                                                                                                                       |        |
| 33   | Dust Arrest Frequency           | uint8  | r,w,n  | 1 Once, 2 Twice, 3 Triple                                                                                                                                                                                                                                                                                             |        |
| 34   | Auto Mop Dry                    | bool   | r,w,n  |                                                                                                                                                                                                                                                                                                                       |        |
| 35   | Auto Water Change               | bool   | r,w,n  |                                                                                                                                                                                                                                                                                                                       |        |
| 36   | Use Detergent                   | bool   | r,w,n  |                                                                                                                                                                                                                                                                                                                       |        |
| 66   | **Fault Ids**                   | string | r,n    | live fault list `{"ts": ..., "fault": [codes]}`; `[0]` = no active fault                                                                                                                                                                                                                                              | ✓      |
| 73   | Carpet Cleaning Method          | uint8  | r,w,n  | 0 Self Adaption, 1 Avoid, 2 Ignore, 3 Span                                                                                                                                                                                                                                                                            |        |
| 74   | **Sweep Route**                 | uint8  | r,w,n  | 1 Quick, 2 Daily, 3 Careful                                                                                                                                                                                                                                                                                           | ✓      |
| 75   | **Obstacle Avoidance Strategy** | uint8  | r,w,n  | 0 Less Collisions, 1 High Coverage                                                                                                                                                                                                                                                                                    | ✓      |
| 76   | Carpet Deep Cleaning            | bool   | r,w,n  |                                                                                                                                                                                                                                                                                                                       |        |
| 82   | Auto Dust Arrest Power Level    | uint8  | r,w,n  | 0 Silent, 1 Normal, 2 Strong                                                                                                                                                                                                                                                                                          |        |
| 83   | Worry Free Clean Mode           | uint8  | r,w,n  | 0 Silent, 1 Deep Clean, 2 Standard                                                                                                                                                                                                                                                                                    |        |
| 84   | Wash Mop Water Temperature      | uint8  | r,w,n  | 0 Ordinary, 1 Warm, 2 Hot, 3 Smart                                                                                                                                                                                                                                                                                    |        |

(For the full property list incl. piid 24/27/38–72/77–81, query the published
spec instance on miot-spec.org — see section 1.)

**Actions** (SIID 2)

| aiid | name                                | in                   | mapped |
|------|-------------------------------------|----------------------|--------|
| 1    | **Start Sweep**                     | —                    | ✓      |
| 2    | **Stop Sweeping**                   | —                    | ✓      |
| 3    | **Stop And Gocharge** (return home) | —                    | ✓      |
| 4    | Start Only Sweep                    | —                    |        |
| 5    | Start Mop                           | —                    |        |
| 6    | Start Sweep Mop                     | —                    |        |
| 7    | **Pause Sweeping**                  | —                    | ✓      |
| 8    | Continue Sweep                      | —                    |        |
| 9    | Start Custom Sweep                  | —                    |        |
| 11   | Get Room Configs                    | [15]                 |        |
| 12   | Set Zone                            | [12]                 |        |
| 13   | Set Room Clean Configs              | [16]                 |        |
| 16   | **Start Vacuum Room Sweep**         | [15] Vacuum Room IDs | ✓ (in_piid 15) |
| 17   | Start Build Map                     | —                    |        |
| 18   | **Start Dust Arrest**               | —                    | ✓      |
| 19   | Start Mop Wash                      | —                    |        |
| 20   | Start Dry                           | —                    |        |
| 21   | Start Eject                         | —                    |        |
| 31   | Stop Mop Wash                       | —                    |        |
| 32   | Stop Dry                            | —                    |        |
| 37   | Start Zone Sweep                    | [12]                 |        |
| 45   | Start Water Self Check              | —                    |        |

(Order-clean, remote-control, build-map, user-sweep actions aiid 23–48 in raw JSON.)

**Events** (SIID 2): 1 Build Map Complete · 2 Sweep Complete · 3 Dust Arrest Complete ·
4 Mop Wash Complete · 5 Dry Complete

### SIID 3 — Battery

| piid | name                | values                                          | mapped |
|------|---------------------|-------------------------------------------------|--------|
| 1    | **Battery Level**   | 0–100 %                                         | ✓      |
| 2    | **Charging State**  | 1 Charging, 2 Not Charging, 3 Not Chargeable    | ✓      |
| 3    | Voltage             | uint16                                          |        |

Action `aiid 1` = **Start Charge** (alternative return-to-dock).

### SIID 4 — Alarm

- piid 1 Alarm (bool, r/w) · piid 2 Volume (0–100 %, r/w)

### SIID 5 — Physical Control Locked

- piid 1 Physical Control Locked (bool, r/w) · piid 2 Current Lock (bool, r)

### SIID 6 — Identify

- **aiid 1 Identify** (locate) ✓

### SIID 9 — Mop

- piid 1 Mop Life Level (0–100 %) · piid 2 Mop Left Time (hours) · **aiid 1 Reset Mop Life**

### SIID 10 — Vacuum Map

| piid | name                | mapped |
|------|---------------------|--------|
| 1    | **Map Obj Name**    | ✓      |
| 2    | Trajectory Obj Name |        |
| 3    | Clean Record        |        |
| 4    | Vacuum Position     |        |
| 6    | Current Map Id (uint32) |    |
| 7    | Carpet Obj Name     |        |
| 13   | Backup Map List     |        |

Actions: 1 Clear Map · 2 Delete Map [6] · 3 Set Map [6] · 4 Save Map · 5 Auto Room
Partition · 6 Set Map Name [8] · 8 Restore Map [6]

### SIID 11 — No Disturb

- piid 1 No Disturb (bool, r/w) · piid 2 Enable Time Period (uint32, r/w) · piid 3 Current No Disturb (r)

### SIID 12 / 13 — Main / Side Cleaning Brush

- piid 1 Brush Life Level (0–100 %) · piid 2 Brush Left Time (hours) · **aiid 1 Reset Brush Life**

### SIID 14 — Filter

- piid 1 Filter Life Level (0–100 %) · piid 2 Filter Left Time (hours) · **aiid 1 Reset Filter Life**

### SIID 15 — Voice Management

- piid 1 Target Voice · piid 3 Download Status · piid 4 Download Progress ·
  aiid 1 Download Voice [1,5,6] · aiid 2 Get Download Status

### SIID 18 — Detergent Management

- piid 1 Detergent Left Level (0–100 %) · piid 2 Self Delivery (bool) ·
  piid 3 Self Delivery Level (0 Few…3 Lots Of) · aiid 1 Reset Detergent Level

### SIID 19 — Dust Bag

- piid 1 Dust Bag Life Level (0–100 %) · piid 2 Dust Bag Left Time (hours) · aiid 1 Reset Dust Bag Life

### SIID 1 — Device Information

- piid 1 Manufacturer · 2 Model · 3 Device ID · 4 Firmware Version · 5 Serial Number

### SIID 20 — custom (vendor-specific, mostly map/history blobs)

- aiid 1 get-history-obj [2]→[1] · aiid 2 get-user-define [2]→[1] · aiid 3 set-stop-upload-map [2]

---

## 5. Spec of `xiaomi.vacuum.ov71gl` (S40 Pro, v1) relative to the X20 Max

Source: `urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-ov71gl:1` (the only
published revision). The S40 Pro is an export-only product: its spec is not
served by the Mainland China cloud, so the account must be logged into the
region that sold the unit (Europe for EU units) for discovery to find it.

Every SIID/PIID/AIID listed in section 4 that this integration reads or invokes
is identical on the S40 Pro. Differences worth knowing:

| Area | S40 Pro (`ov71gl`) |
|------|--------------------|
| `status` (2/2) | adds `22 StationAssistingCleaning`, `23 StationAssistingCleaned`, `24 GoChargeInStationAssistingCleaning` |
| `sweep-type` (2/5) | adds `8 Appointment`, `9 Linkage`, `10 Fast`, `11 AI Hosting` |
| Dock | ships with a plain charging dock; the spec still lists `start-dust-arrest` (2/18), `start-mop-wash` (2/19), `stop-mop-wash` (2/31), `stop-dry` (2/32) but there is no `start-dry` (2/20) and no hardware behind them — the integration wires none |
| Services | no `18 Detergent Management`, no `19 Dust Bag`; adds `16 imu` (calibration action) |
| Extra properties on SIID 2 | `41 hot-water-mop-wash`, `56 sweep-ai-object`, `63/64 cut-hair-config`, `85-90` cleaning statistics and drying progress, `96 sweep-mop-status`, `97/98` sewage / water tank status, `99 sill`, `100/101` base-station / host water tank status — not read by the integration |
| Extra actions on SIID 2 | `10 get-zone-configs`, `22 start-call-clean`, `44 stop-cut-hair`, `49-59` station cleaning, skip / final / temporary room and zone cleaning, tank emptying, spot cleaning, `62-64` object clean and station self-cleaning |
| Zone cleaning | not usable from this integration — see below |
| Faults | publishes `100027` ("Sewage tank is full or not installed") in `Fault Ids` permanently — a station check the dockless retail unit can never satisfy; listed in the spec's `ignored_fault_codes` |

### Zone (rectangle) cleaning is not reproducible on this firmware

Captured from a physical S40 Pro on firmware `4.5.8_0053` while the Mi Home app
cleaned a rectangle the user drew:

```
sweep-type  (2/5)  = 2            # Zone
status      (2/2)  = 4            # Sweeping
current-cleaning-config (2/40) =
  {"zones":[[-1139,-380,-1139,-1731,290,-1731,290,-380]],
   "clean_mode":2,"is_ai_cleaning":false,"dirty_cleaning":false}
```

So a zone is a **flat array of four corners** in map millimetres, ordered
left/top, left/bottom, right/bottom, right/top — the same flat convention as
`fb_point` in the map payload, not an `{x1, y1, x2, y2}` object.

Replaying it does not work. `zone-ids` (2/12) stayed empty for the whole
cleaning run, so it is not where the app puts the geometry, and
`start-vacuum-zone-sweep` (2/37) was called with that exact polygon — alone,
with `clean_mode`, and with `map_uid` — without the robot reacting at all. The
device answers `code: 0` to every payload including malformed ones, so an
acknowledgement proves nothing. The same conclusion was reached independently
on the sibling X20 Pro (`d102gl`), where writing `zone-ids` directly is
rejected as not writable.

About twenty variants were tried in total and **every one was inert**:

- actions: `start-zone-sweep` (2/37), `set-zone` (2/12) and
  `temporary-cleaning-zone` (2/55, which takes `common-params` 2/24 instead of
  `zone-ids`);
- geometry: the captured polygon as a `{"zones": […]}` object, as a bare
  nested array, as a comma-separated string, and as a flat list, with and
  without `clean_mode` and `map_uid`;
- parameter encoding: both piid-tagged (`[{"piid": 12, "value": …}]`) and
  bare (`[…]`), since the S20+ room flow uses bare values;
- sequencing: each start action alone, and `set-zone` followed by
  `start-zone-sweep`, by `start-custom-sweep` (2/9) and with an empty input.

Only `start-sweep` (2/1) ever reacted, and it simply began an ordinary
whole-home clean with `sweep-type 1` and no `zones` in the config, i.e. it
ignored the zone entirely. Beware of that false positive: on this firmware a
status change alone does not mean the zone was accepted. The check is
`sweep-type == 2` or a `zones` key in `current-cleaning-config`.

What is left to try:

- The **cloud** transport, which is what the Mi Home app uses.
  `POST /miotspec/action` returns real parameter errors (`-704040005`
  structure mismatch, `-704030023` not writable) where the local transport
  answers `code: 0` regardless, so it can tell a rejected payload from an
  ignored one. Nothing more can be concluded locally.
- The app's saved "custom cleanup" presets, which store the same flat polygon
  under `mode_data` in `user-define-sweep-cfg` (2/42);
  `start-user-define-sweep` (2/42) then takes the preset id as a string. That
  would clean a preset the user saved in the app rather than an arbitrary
  rectangle.

A **spot clean started from the app is the same mechanism**, just a smaller
rectangle: a second capture of an app-driven spot clean reported
`{"zones":[[-1168,25,-1168,-614,-477,-614,-477,25]],"clean_mode":2,…}`, about
70 cm by 64 cm, again with `sweep-type 2`. So zones and spots share one code
path on this device, and whatever unlocks one unlocks the other.

### Spot cleaning is published but inert

`spot-cleaning` (2/59) and `start-call-clean` (2/22) both exist on the S40 Pro
and take no parameters, but neither does anything on firmware `4.5.8_0053`.
Each was called with the robot charging on its dock and again with the robot
standing away from it, and the status never left the idle set. As everywhere
else on this device, the answer was `code: 0`.

That is why the vacuum entity does not advertise
`VacuumEntityFeature.CLEAN_SPOT`: `vacuum.clean_spot` would report success
while the robot stayed put. The Mi Home app offers whole-home, per-room,
drawn-area and furniture cleaning for this model, but no spot or point mode,
so these two actions look like more of the spec template's unbacked hardware,
alongside the dock actions.

### Manual driving does work

`enter-remote` (2/28), `remote-control` (2/26, taking `button-type` on piid 39)
and `exit-remote` (2/29) are honoured: sending press-forward then
release-forward drives the robot off its dock, and the status moves from
`2 Charging` to `1 Idle`. The integration does not expose this, but it is
available for anyone who wants a manual-driving control.

## 6. Fault codes and their localized text

The **Device Fault** property (siid 2 / piid 3) reports a **large, device-specific
numeric code** (e.g. `210009`), not a small enum. There is **no static code→text table**
for this model anywhere: not in the miot-spec instance (no `value-list`, verified for v1
and v2), not in `spec_multi_language` (the fault property has no translatable entries —
only the *status* value-list is translated), and there is no downloadable plugin
(`fetch_plugin`, `get_config_info_new`, `get_standard_operation` all return nothing for
d109gl — it renders with the built-in generic spec engine).

The human-readable, **already-localized** text seen in the Mi Home app is delivered by the
Xiaomi cloud as a **device message** (push), not by the client:

- `POST /v2/message/v2/list` body `{"did": "<did>", "type": 6, "timestamp": 0, "limit": 50, "force_read": false}`
- Each message: `title` = localized text (account language), `params.body.event` = `"<siid>.<piid>"`
  (`"2.3"` is the Device Fault property), `params.body.value` = `[<fault code>]`.

Verified real example (account locale pt-BR):

| event | code | title |
|---|---|---|
| `2.3` | `210009` | Não foi possível voltar à base para carregar. Mova o robô-aspirador para a base de carregamento. |

(Events with an empty `value`, e.g. `"2.2"` "Limpeza concluída", are status notices, not faults.)

**Known codes.** Values in the `1000xx` range are the robot/station hardware checks
(`100027` = sewage tank full or not installed, observed permanently on the dockless
S40 Pro); `21xxxx` are navigation failures (`210009` = could not return to the dock).
A model that reports a code for hardware it does not have lists it in its
`ModelSpec.ignored_fault_codes` so the coordinator drops it — see `spec/ov71gl.py`.

This integration therefore resolves fault text at runtime: `cloud.XiaomiCloud.async_fault_text(code)`
reads this feed and caches `{code: title}`; the coordinator attaches it to the fault as
`fault_text`, and the Error sensor displays it (falling back to `Error <code>` if the cloud
has no message for that code yet).
