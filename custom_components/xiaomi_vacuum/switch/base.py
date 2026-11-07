"""Shared base for MIoT-backed on/off switches."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory

from ..entity import XiaomiVacuumEntity  # noqa: TID252

if TYPE_CHECKING:
    from ..spec import Property  # noqa: TID252


class _XiaomiVacuumSwitch(XiaomiVacuumEntity, SwitchEntity):
    """
    A MIoT on/off setting.

    Most of them are uint8 ``0``/``1`` properties; ``_boolean`` marks the ones
    published as a real bool, which the device expects to be written back as
    one.
    """

    _attr_entity_category = EntityCategory.CONFIG

    _property_name: ClassVar[Property]
    _boolean: ClassVar[bool] = False

    @property
    def unique_id(self) -> str:
        """Return a stable unique id derived from the translation key."""
        return f"{self.coordinator.config_entry.entry_id}_{self._attr_translation_key}"

    @property
    def is_on(self) -> bool | None:
        """Return whether the setting is on, or None when unknown."""
        value = self.coordinator.data.get(self._property_name)
        return bool(value) if isinstance(value, int) else None

    async def async_turn_on(self, **kwargs: object) -> None:  # noqa: ARG002
        """Turn the setting on."""
        await self._async_write(on=True)

    async def async_turn_off(self, **kwargs: object) -> None:  # noqa: ARG002
        """Turn the setting off."""
        await self._async_write(on=False)

    async def _async_write(self, *, on: bool) -> None:
        value: bool | int = on if self._boolean else int(on)
        client = self.coordinator.config_entry.runtime_data.client
        await client.async_set_property(self._property_name, value=value)
        self._patch_state(**{self._property_name: value})
        self._schedule_refresh()
