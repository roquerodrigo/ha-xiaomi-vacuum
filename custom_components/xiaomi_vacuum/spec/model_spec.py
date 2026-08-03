"""Everything the integration needs to know about one vacuum model."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Literal, TypedDict

from .capability import Capability
from .entity_key import EntityKey
from .property import Property

if TYPE_CHECKING:
    from homeassistant.components.vacuum.const import VacuumActivity

    from .addresses import MiotActionAddress, MiotPropertyAddress
    from .model_actions import ModelActions

# How the live fault is read. d109gl publishes a `Fault Ids` JSON list
# ({"fault":[codes]}); b108gl publishes a plain `fault` uint32 (0 == healthy).
FaultKind = Literal["ids", "simple"]

# How room cleaning is initiated.
# - "direct": a single `start-vacuum-room-sweep` action takes the room ids
#   as input (X20 Max).
# - "config_then_custom": the app first marks the target rooms via
#   `set-room-clean-configs` (setting their `on` flag), then fires
#   `start-custom-sweep` with no params (S20+). Captured from the Mi Home app.
RoomCleanStrategy = Literal["direct", "config_then_custom"]


class StatusDef(TypedDict):
    """Per-status-code metadata: HA activity, slug, and idle flag."""

    activity: VacuumActivity
    slug: str
    is_idle: bool


#: Maps each optional :class:`Capability` to the :class:`EntityKey` it gates.
_CAPABILITY_ENTITIES: dict[Capability, EntityKey] = {
    Capability.DUST_ARREST: EntityKey.DUST_ARREST_BUTTON,
    Capability.SWEEP_ROUTE: EntityKey.SWEEP_ROUTE_SELECT,
    Capability.OBSTACLE_AVOIDANCE: EntityKey.OBSTACLE_AVOIDANCE_SELECT,
}

#: Entities every supported vacuum exposes regardless of capabilities.
#: Includes the platforms whose creation is otherwise unconditional
#: (vacuum entity, sensors, binary sensor, map image) so the entity-key
#: registry stays the single source of truth for what a model exposes.
_BASE_ENTITIES: frozenset[EntityKey] = frozenset(
    {
        EntityKey.VACUUM,
        EntityKey.MAP_IMAGE,
        EntityKey.BATTERY_SENSOR,
        EntityKey.STATUS_SENSOR,
        EntityKey.ERROR_SENSOR,
        EntityKey.ERROR_CODE_SENSOR,
        EntityKey.MOP_LIFE_SENSOR,
        EntityKey.MAIN_BRUSH_LIFE_SENSOR,
        EntityKey.SIDE_BRUSH_LIFE_SENSOR,
        EntityKey.FILTER_LIFE_SENSOR,
        EntityKey.BATTERY_CHARGING_SENSOR,
        EntityKey.MOP_PAD_SENSOR,
        EntityKey.SWEEP_MOP_TYPE_SELECT,
        EntityKey.CLEAN_TIMES_SELECT,
        EntityKey.MOP_WATER_LEVEL_SELECT,
    }
)

#: Names of the dict-typed fields wrapped in read-only views by
#: :meth:`ModelSpec.__post_init__`.
MAPPING_FIELDS: tuple[str, ...] = (
    "property_mapping",
    "status",
    "fan_speeds",
    "sweep_mop_types",
    "clean_times",
    "mop_water_levels",
    "charging_state_slugs",
    "send_commands",
    "sweep_routes",
    "obstacle_avoidances",
)


@dataclass(frozen=True)
class ModelSpec:
    """Everything model-specific the integration needs at runtime."""

    model: str
    name: str
    property_mapping: dict[Property, MiotPropertyAddress]
    actions: ModelActions
    status: dict[int, StatusDef]
    fan_speeds: dict[str, int]
    sweep_mop_types: dict[str, int]
    clean_times: dict[str, int]
    mop_water_levels: dict[str, int]
    charging_state_slugs: dict[int, str]
    send_commands: dict[str, MiotActionAddress]
    fault_kind: FaultKind
    room_clean_strategy: RoomCleanStrategy
    # Optional per-model enumerations, present only when the model exposes the
    # matching property (gated by Capability.SWEEP_ROUTE / OBSTACLE_AVOIDANCE).
    # Kept on the spec — not module-level — so a future vacuum publishing a
    # different value table gets its own instead of the X20 Max's.
    sweep_routes: dict[str, int] = field(default_factory=dict)
    obstacle_avoidances: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Wrap the mutable dict fields in read-only views."""
        # ``frozen=True`` only blocks attribute reassignment; the dict fields are
        # still mutable and would otherwise be shared across instances (and with
        # ``MiotDevice`` via ``property_mapping``). ``object.__setattr__`` is the
        # sanctioned way to normalise fields inside a frozen dataclass.
        for name in MAPPING_FIELDS:
            object.__setattr__(self, name, MappingProxyType(getattr(self, name)))

    @property
    def status_to_activity(self) -> dict[int, VacuumActivity]:
        """Status code → HA activity, derived from :attr:`status`."""
        return {code: s["activity"] for code, s in self.status.items()}

    @property
    def status_slugs(self) -> dict[int, str]:
        """Status code → translation slug, derived from :attr:`status`."""
        return {code: s["slug"] for code, s in self.status.items()}

    @property
    def idle_statuses(self) -> frozenset[int]:
        """Status codes that count as parked/idle (a fresh start is safe)."""
        return frozenset(code for code, s in self.status.items() if s["is_idle"])

    def status_code_for(self, activity: VacuumActivity) -> int:
        """
        First status code whose activity matches ``activity``.

        Used by optimistic UI patches so a command reports the same activity the
        device will confirm on the next poll, without the platform hard-coding
        per-model status codes (X20 Max and S20+ already diverge elsewhere).
        Order is insertion order of :attr:`status`, which lists the canonical
        representative (e.g. ``sweeping`` for CLEANING) first.
        """
        for code, definition in self.status.items():
            if definition["activity"] is activity:
                return code
        msg = f"No status code maps to activity {activity!r}"
        raise ValueError(msg)

    @property
    def capabilities(self) -> frozenset[Capability]:
        """The set of capabilities this model advertises, derived from its spec."""
        caps: set[Capability] = set()
        if self.actions.start_dust_arrest is not None:
            caps.add(Capability.DUST_ARREST)
        if Property.SWEEP_ROUTE in self.property_mapping:
            caps.add(Capability.SWEEP_ROUTE)
        if Property.OBSTACLE_AVOIDANCE_STRATEGY in self.property_mapping:
            caps.add(Capability.OBSTACLE_AVOIDANCE)
        return frozenset(caps)

    @property
    def entities(self) -> frozenset[EntityKey]:
        """Entities to create for this model: base set plus capability-gated ones."""
        keys = set(_BASE_ENTITIES)
        for cap in self.capabilities:
            if (key := _CAPABILITY_ENTITIES.get(cap)) is not None:
                keys.add(key)
        return frozenset(keys)

    @property
    def fan_speed_names(self) -> dict[int, str]:
        """Reverse of :attr:`fan_speeds` (value→slug)."""
        return {v: k for k, v in self.fan_speeds.items()}

    @property
    def sweep_mop_type_names(self) -> dict[int, str]:
        """Reverse of :attr:`sweep_mop_types` (value→slug)."""
        return {v: k for k, v in self.sweep_mop_types.items()}

    @property
    def clean_times_names(self) -> dict[int, str]:
        """Reverse of :attr:`clean_times` (value→slug)."""
        return {v: k for k, v in self.clean_times.items()}

    @property
    def mop_water_level_names(self) -> dict[int, str]:
        """Reverse of :attr:`mop_water_levels` (value→slug)."""
        return {v: k for k, v in self.mop_water_levels.items()}
