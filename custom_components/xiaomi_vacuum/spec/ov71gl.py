"""
Spec for the Xiaomi Robot Vacuum S40 Pro — ``xiaomi.vacuum.ov71gl``.

Source: ``urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-ov71gl:1`` (the only
published revision). The S40 Pro is an export-only product: its spec is not
served by the Mainland China cloud, so the config flow must use another region
(Europe for EU units) for the vacuum to be discovered.

The vacuum-service layout is the X20 Max's (``d109gl.py``): every SIID/PIID/AIID
this integration reads or invokes is identical, so the spec is derived from it
and only states where the two diverge. Anything added to the X20 Max reaches
the S40 Pro too, unless it is removed here:

- status publishes three extra codes (22 StationAssistingCleaning, 23
  StationAssistingCleaned, 24 GoChargeInStationAssistingCleaning)
- the retail S40 Pro ships with a plain charging dock. The spec template still
  lists dust-arrest / mop-wash actions, but no dock hardware honours them, so no
  dock action is wired: no dust-arrest button, no mop-wash / dry send_commands
- no detergent (SIID 18) or dust-bag (SIID 19) services, no start-dry action
- zone cleaning is enabled via the shared X20 Max ``start-zone-sweep`` action
  (2/37); earlier unsuccessful payload attempts are documented in
  ``XIAOMI_VACUUM_API.md`` §5
- no custom cleanings: the action and its list are only verified on the X20 Max
- no dock settings: mop washing and its frequency, wash water and temperature,
  drying time, auto dust collection and its frequency, and auto mop drying
  configure station hardware the S40 Pro lacks (its spec does not even publish
  the mop-wash switch, 2/28, nor the wash water temperature, 2/84)
- the dockless hardware still runs the station's sewage-tank check and reports
  its permanent failure as fault 100027, which ``_PHANTOM_FAULTS`` drops
- taking the water tank or dust bin out raises 210020 / 210005, which
  ``_NOTICE_FAULTS`` keeps on the error sensors without forcing ERROR
"""

from __future__ import annotations

from dataclasses import replace

from .d109gl import D109GL
from .property import Property
from .status_slug import StatusSlug

_ACTIONS = replace(
    D109GL.actions,
    start_user_define_sweep=None,
    start_dust_arrest=None,
    start_mop_wash=None,
    start_dry=None,
    stop_mop_wash=None,
    stop_dry=None,
)

# Settings of the auto-wash dock (``d109gl.py``) that the plain charging dock
# cannot honour.
_DOCK_SETTINGS = frozenset(
    {
        Property.MOP_WASH,
        Property.MOP_WASH_FREQUENCY,
        Property.MOP_WASH_AREA_INTERVAL,
        Property.MOP_WASH_TIME_INTERVAL,
        Property.MOP_DRYING_TIME,
        Property.AUTO_DUST_COLLECTION,
        Property.AUTO_MOP_DRYING,
        Property.MOP_WASH_WATER_MODE,
        Property.MOP_WASH_TEMPERATURE,
        Property.DUST_COLLECTION_FREQUENCY,
    }
)

# Codes 22-24 are the station-assisted washing cycle the S40 Pro adds over the
# X20 Max: rinsing at the dock, rinse finished, returning to the dock to rinse.
_STATUS: dict[int, StatusSlug] = {
    **D109GL.status,
    22: StatusSlug.STATION_ASSISTING_CLEANING,
    23: StatusSlug.STATION_ASSISTING_CLEANED,
    24: StatusSlug.GO_CHARGE_IN_STATION_ASSISTING_CLEANING,
}

# Fault codes the S40 Pro reports permanently for dock hardware it does not
# have. 100027 ("Sewage tank is full or not installed") is published in the live
# `Fault Ids` list from boot and never clears: the firmware is shared with the
# station-equipped variants of the family and keeps running the sewage-tank
# check, while the retail S40 Pro ships with a plain charging dock that has no
# sewage tank at all. The Mi Home app knows the dock type and shows nothing, so
# the integration must drop the code too — otherwise the vacuum entity is stuck
# in ERROR forever. Observed on a physical unit, firmware 4.5.8_0053, docked and
# fully charged (status 9).
_PHANTOM_FAULTS = frozenset({100027})

# Maintenance notices the S40 Pro publishes in `Fault Ids` while the user
# services it, cleared on their own once the part is back in place: 210020 when
# the water tank is taken out to be refilled, 210005 when the dust bin is taken
# out to be emptied. Observed on a physical unit.
_NOTICE_FAULTS = frozenset({210005, 210020})

OV71GL = replace(
    D109GL,
    model="xiaomi.vacuum.ov71gl",
    name="Xiaomi Robot Vacuum S40 Pro",
    actions=_ACTIONS,
    status=_STATUS,
    property_mapping={
        name: binding
        for name, binding in D109GL.property_mapping.items()
        if name is not Property.USER_DEFINE_SWEEP_CONFIG and name not in _DOCK_SETTINGS
    },
    mop_wash_frequencies={},
    mop_wash_area_intervals={},
    mop_drying_times={},
    mop_wash_water_modes={},
    mop_wash_temperatures={},
    dust_collection_frequencies={},
    ignored_fault_codes=_PHANTOM_FAULTS,
    notice_fault_codes=_NOTICE_FAULTS,
)
