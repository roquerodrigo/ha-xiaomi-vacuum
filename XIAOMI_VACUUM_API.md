# Xiaomi Home — Vacuum Control API

How the Xiaomi Home app controls vacuums via the **miot-spec** protocol, the cloud
transport, and the **complete spec for `xiaomi.vacuum.d109gl`** (this integration's target
model). All identifiers below come from the public miot-spec service.

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
| 3    | **Device Fault**                | uint32 | r,n    | 0–420000                                                                                                                                                                                                                                                                                                              | ✓      |
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
| 73   | Carpet Cleaning Method          | uint8  | r,w,n  | 0 Self Adaption, 1 Avoid, 2 Ignore, 3 Span                                                                                                                                                                                                                                                                            |        |
| 74   | **Sweep Route**                 | uint8  | r,w,n  | 1 Quick, 2 Daily, 3 Careful                                                                                                                                                                                                                                                                                           | ✓      |
| 75   | **Obstacle Avoidance Strategy** | uint8  | r,w,n  | 0 Less Collisions, 1 High Coverage                                                                                                                                                                                                                                                                                    | ✓      |
| 76   | Carpet Deep Cleaning            | bool   | r,w,n  |                                                                                                                                                                                                                                                                                                                       |        |
| 82   | Auto Dust Arrest Power Level    | uint8  | r,w,n  | 0 Silent, 1 Normal, 2 Strong                                                                                                                                                                                                                                                                                          |        |
| 83   | Worry Free Clean Mode           | uint8  | r,w,n  | 0 Silent, 1 Deep Clean, 2 Standard                                                                                                                                                                                                                                                                                    |        |
| 84   | Wash Mop Water Temperature      | uint8  | r,w,n  | 0 Ordinary, 1 Warm, 2 Hot, 3 Smart                                                                                                                                                                                                                                                                                    |        |

(Full property list incl. piid 24/27/38–72/77–81 in `resources/d109gl_spec.v2.json`.)

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

## 5. Fault codes and their localized text

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

This integration therefore resolves fault text at runtime: `cloud.XiaomiCloud.async_fault_text(code)`
reads this feed and caches `{code: title}`; the coordinator attaches it to the fault as
`fault_text`, and the Error sensor displays it (falling back to `Error <code>` if the cloud
has no message for that code yet).
