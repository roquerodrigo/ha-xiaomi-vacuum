"""Shared base for MIoT-backed select entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory

from ..entity import XiaomiVacuumEntity  # noqa: TID252

if TYPE_CHECKING:
    from ..spec import Property  # noqa: TID252


class _XiaomiVacuumSelect(XiaomiVacuumEntity, SelectEntity):
    """
    Base for a MIoT property exposed as a slug-valued select.

    Subclasses pin ``_property_name`` (the :class:`Property` they read/write) and
    override :attr:`_slug_to_value` with the slug→value map for the active model.
    Both come from the active model's spec so the option list matches what the
    device actually supports.
    """

    _attr_entity_category = EntityCategory.CONFIG

    _property_name: Property

    @property
    def _slug_to_value(self) -> dict[str, int]:
        """Slug→value map; subclasses must override with the active model's spec."""
        raise NotImplementedError

    @property
    def _value_to_slug(self) -> dict[int, str]:
        return {v: k for k, v in self._slug_to_value.items()}

    @property
    def unique_id(self) -> str:
        """Return a stable unique id derived from the translation key."""
        return f"{self.coordinator.config_entry.entry_id}_{self._attr_translation_key}"

    @property
    def options(self) -> list[str]:
        """Return the selectable slugs (the keys of the slug->value map)."""
        return list(self._slug_to_value)

    @property
    def current_option(self) -> str | None:
        """Return the current option as a slug, or None when unknown."""
        value = self.coordinator.data.get(self._property_name)
        return self._value_to_slug.get(int(value)) if isinstance(value, int) else None

    async def async_select_option(self, option: str) -> None:
        """Set the option on the device, with optimistic update."""
        client = self.coordinator.config_entry.runtime_data.client
        value = self._slug_to_value[option]
        await client.async_set_property(self._property_name, value)
        self._patch_state(**{self._property_name: value})
        self._schedule_refresh()
