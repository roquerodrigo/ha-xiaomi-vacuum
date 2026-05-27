"""Shared base for MIoT-backed select entities."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.entity import EntityCategory

from ..entity import XiaomiVacuumEntity  # noqa: TID252

if TYPE_CHECKING:
    from ..coordinator import XiaomiVacuumDataUpdateCoordinator  # noqa: TID252


class _XiaomiVacuumSelect(XiaomiVacuumEntity, SelectEntity):
    """Base for a MIoT property exposed as a slug-valued select."""

    _attr_entity_category = EntityCategory.CONFIG

    _property_name: ClassVar[str]
    _slug_to_value: ClassVar[dict[str, int]]
    _value_to_slug: ClassVar[dict[int, str]]

    def __init__(self, coordinator: XiaomiVacuumDataUpdateCoordinator) -> None:
        """Initialize, deriving the unique_id from the translation key."""
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{self._attr_translation_key}"
        )

    @property
    def options(self) -> list[str]:
        """Return the selectable slugs (the keys of the slug->value map)."""
        return list(self._slug_to_value)

    @property
    def current_option(self) -> str | None:
        """Return the current option as a slug, or None when unknown."""
        value = self.coordinator.data.get(self._property_name)
        return (
            self._value_to_slug.get(int(cast("int", value)))
            if value is not None
            else None
        )

    async def async_select_option(self, option: str) -> None:
        """Set the option on the device, with optimistic update."""
        client = self.coordinator.config_entry.runtime_data.client
        value = self._slug_to_value[option]
        await client.async_set_property(self._property_name, value)
        self._patch_state(**{self._property_name: value})
        self._schedule_refresh()
