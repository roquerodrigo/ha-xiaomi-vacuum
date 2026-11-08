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


def _require_action(action: MiotActionAddress | None, name: str) -> MiotActionAddress:
    """
    Return a non-``None`` action or raise at import time.

    Used by ``send_commands`` whitelists that reference optional actions (X20
    Max mop-wash / dry, the mode-specific starts). A bare :func:`typing.cast`
    would silence the type checker without checking anything, so a model
    referencing an action it does not define would store a ``None`` and fail
    with a ``TypeError`` at command time. Raising here surfaces the mismatch at
    import time, where the spec was actually written.
    """
    if action is None:
        msg = f"send_commands entry {name!r} needs an action this model defines"
        raise ValueError(msg)
    return action
