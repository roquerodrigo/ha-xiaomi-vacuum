"""
Spec for the Xiaomi Robot Vacuum S40C — ``xiaomi.vacuum.e101gb``.

Source: ``urn:miot-spec-v2:device:vacuum:0000A006:xiaomi-e101gb:1`` (the only
released revision). A physical unit on firmware ``4.5.6_0111``, signed in to
the Russia cloud, published every polled property this layout reads.

The vacuum-service layout the integration uses is the S40 Pro's
(``ov71gl.py``): every SIID/PIID/AIID it reads or invokes is identical,
including status codes 1-24, so the spec is derived from it and only states
where the two diverge. Anything added to the S40 Pro reaches the S40C too,
unless it is removed here:

- the retail S40C ships with charging dock E101CDZ and a mop tank on the
  robot. The published spec still lists dust-arrest, mop-wash and dry
  actions, plus detergent (SIID 18) and dust-bag (SIID 19) services. That
  hardware is not in the box, so those actions stay unwired, as on the S40 Pro
- room cleaning stays the direct ``start-vacuum-room-sweep`` (2/16, input
  piid 15). This unit's room list was read from property 2/16; the start
  action has not been sent on it
- zone cleaning stays the shared ``start-zone-sweep`` (2/37). The published
  address matches the S40 Pro. A rectangle clean has not been started on an
  S40C
- no custom cleanings, same as the S40 Pro
- ``ignored_fault_codes`` and ``notice_fault_codes`` stay empty. The S40 Pro
  drops 100027 and treats 210005 / 210020 as notices because that unit
  published them. This unit, docked at 95% charge, published ``{"fault": [0]}``
  and neither code, so they are not copied
"""

from __future__ import annotations

from dataclasses import replace

from .ov71gl import OV71GL

E101GB = replace(
    OV71GL,
    model="xiaomi.vacuum.e101gb",
    name="Xiaomi Robot Vacuum S40C",
    ignored_fault_codes=frozenset[int](),
    notice_fault_codes=frozenset[int](),
)
