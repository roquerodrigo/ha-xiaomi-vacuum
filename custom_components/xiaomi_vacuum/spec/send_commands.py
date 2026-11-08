"""The parameterless actions exposed through the vacuum's ``send_command``."""

from __future__ import annotations

#: :class:`ModelActions` fields a model accepts as ``send_command`` names when it
#: defines them. They have no entity of their own (the mode-specific starts) or
#: are useful in automations without one (resuming a job, the dock cycles).
SEND_COMMAND_ACTIONS: tuple[str, ...] = (
    "start_only_sweep",
    "start_mop",
    "start_sweep_mop",
    "continue_sweep",
    "start_mop_wash",
    "stop_mop_wash",
    "start_dry",
    "stop_dry",
)
