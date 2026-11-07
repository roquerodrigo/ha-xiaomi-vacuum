"""Shared base for buttons that fire one parameterless spec action."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from homeassistant.components.button import ButtonEntity

from ..entity import XiaomiVacuumEntity  # noqa: TID252

if TYPE_CHECKING:
    from ..spec.addresses import MiotActionAddress  # noqa: TID252


class _XiaomiVacuumActionButton(XiaomiVacuumEntity, ButtonEntity):
    """
    Fires the :class:`ModelActions` field named by ``_action_name``.

    The button is only created when the active model defines that action (see
    ``ModelSpec.entities``), so the lookup always finds an address.
    """

    _action_name: ClassVar[str]

    @property
    def unique_id(self) -> str:
        """Return a stable unique id derived from the translation key."""
        return f"{self.coordinator.config_entry.entry_id}_{self._attr_translation_key}"

    @property
    def _action(self) -> MiotActionAddress:
        action: MiotActionAddress | None = getattr(
            self.coordinator.spec.actions, self._action_name
        )
        if action is None:
            msg = f"Model has no {self._action_name} action"
            raise RuntimeError(msg)
        return action

    async def async_press(self) -> None:
        """Fire the action, then refresh to pick up the new state."""
        client = self.coordinator.config_entry.runtime_data.client
        await client.async_run_action(self._action)
        self._schedule_refresh()
