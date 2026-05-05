"""Select platform for xiaomi_vacuum (data-driven from SELECT_ENTITIES)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.entity import EntityCategory

from .const import (
    CLEAN_TIMES,
    CLEAN_TIMES_NAMES,
    MOP_WATER_LEVEL_NAMES,
    MOP_WATER_LEVELS,
    OBSTACLE_AVOIDANCE_NAMES,
    OBSTACLE_AVOIDANCES,
    SWEEP_MOP_TYPE_NAMES,
    SWEEP_MOP_TYPES,
    SWEEP_ROUTE_NAMES,
    SWEEP_ROUTES,
)
from .entity import XiaomiVacuumEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import XiaomiVacuumDataUpdateCoordinator
    from .data import XiaomiVacuumConfigEntry


@dataclass(frozen=True)
class _SelectDef:
    """Static metadata for a MIoT-backed select entity."""

    translation_key: str  # also the unique_id suffix
    property_name: str  # key in PROPERTY_MAPPING + coordinator.data
    slug_to_value: dict[str, int]
    value_to_slug: dict[int, str]
    icon: str


SELECT_ENTITIES: tuple[_SelectDef, ...] = (
    _SelectDef(
        "sweep_mop_type",
        "sweep_mop_type",
        SWEEP_MOP_TYPES,
        SWEEP_MOP_TYPE_NAMES,
        "mdi:broom",
    ),
    _SelectDef(
        "clean_times",
        "clean_times",
        CLEAN_TIMES,
        CLEAN_TIMES_NAMES,
        "mdi:repeat",
    ),
    _SelectDef(
        "mop_water_level",
        "mop_water_level",
        MOP_WATER_LEVELS,
        MOP_WATER_LEVEL_NAMES,
        "mdi:water-percent",
    ),
    _SelectDef(
        "sweep_route",
        "sweep_route",
        SWEEP_ROUTES,
        SWEEP_ROUTE_NAMES,
        "mdi:map-marker-path",
    ),
    _SelectDef(
        "obstacle_avoidance_strategy",
        "obstacle_avoidance_strategy",
        OBSTACLE_AVOIDANCES,
        OBSTACLE_AVOIDANCE_NAMES,
        "mdi:radar",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: XiaomiVacuumConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up all select entities."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        XiaomiVacuumSelect(coordinator, definition) for definition in SELECT_ENTITIES
    )


class XiaomiVacuumSelect(XiaomiVacuumEntity, SelectEntity):
    """Generic MIoT-backed select."""

    _attr_entity_category = EntityCategory.CONFIG
    # _attr_options is set per-instance in __init__
    _attr_options: ClassVar[list[str]] = []

    def __init__(
        self,
        coordinator: XiaomiVacuumDataUpdateCoordinator,
        definition: _SelectDef,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._def = definition
        self._attr_translation_key = definition.translation_key
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{definition.translation_key}"
        )
        self._attr_options = list(definition.slug_to_value)
        self._attr_icon = definition.icon

    @property
    def current_option(self) -> str | None:
        """Return current option as slug."""
        value = self.coordinator.data.get(self._def.property_name)
        return self._def.value_to_slug.get(int(value)) if value is not None else None

    async def async_select_option(self, option: str) -> None:
        """Set the option on the device, with optimistic update."""
        client = self.coordinator.config_entry.runtime_data.client
        value = self._def.slug_to_value[option]
        await client.async_set_property(self._def.property_name, value)
        self._patch_state(**{self._def.property_name: value})
        self._schedule_refresh()
