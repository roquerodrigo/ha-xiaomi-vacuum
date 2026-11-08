"""MIoT action addresses for one vacuum model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .addresses import MiotActionAddress, MiotActionInputAddress


@dataclass(frozen=True)
class ModelActions:
    """MIoT action addresses (``{siid, aiid}`` and optional ``in_piid``)."""

    start_sweep: MiotActionAddress
    stop_sweeping: MiotActionAddress
    return_home: MiotActionAddress
    pause_sweeping: MiotActionAddress
    continue_sweep: MiotActionAddress
    identify: MiotActionAddress
    # Mode-specific starts. The Xiaomi in-house models publish one action per
    # sweep/mop mode; Dreame-built models (X20+) have none and start in the mode
    # selected in the app instead.
    start_only_sweep: MiotActionAddress | None = None
    start_mop: MiotActionAddress | None = None
    start_sweep_mop: MiotActionAddress | None = None
    start_zone_sweep: MiotActionInputAddress | None = None
    start_user_define_sweep: MiotActionInputAddress | None = None
    # Dock-only actions; None when the model has no such hardware (S20+).
    start_dust_arrest: MiotActionAddress | None = None
    start_mop_wash: MiotActionAddress | None = None
    start_dry: MiotActionAddress | None = None
    stop_mop_wash: MiotActionAddress | None = None
    stop_dry: MiotActionAddress | None = None
    # Consumable life resets; None when the model publishes no reset action.
    reset_main_brush: MiotActionAddress | None = None
    reset_side_brush: MiotActionAddress | None = None
    reset_filter: MiotActionAddress | None = None
    reset_mop: MiotActionAddress | None = None
