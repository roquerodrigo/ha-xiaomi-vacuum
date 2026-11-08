"""Everything the integration needs to know about one vacuum model."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Literal

from .capability import Capability
from .cleaning_job_signal import CleaningJobSignal
from .entity_key import EntityKey
from .property import Property
from .status_catalog import CANONICAL_STATUSES, STATUS_MEANINGS

if TYPE_CHECKING:
    from homeassistant.components.vacuum.const import VacuumActivity

    from .addresses import MiotActionAddress, MiotPropertyAddress
    from .model_actions import ModelActions
    from .status_slug import StatusSlug

# How the live fault is read. d109gl publishes a `Fault Ids` JSON list
# ({"fault":[codes]}); b108gl publishes a plain `fault` uint32 (0 == healthy).
FaultKind = Literal["ids", "simple"]

# How room cleaning is initiated.
# - "direct": a single `start-vacuum-room-sweep` action takes the room ids
#   as input (X20 Max).
# - "config_then_custom": the app first marks the target rooms via
#   `set-room-clean-configs` (setting their `on` flag), then fires
#   `start-custom-sweep` with no params (S20+). Captured from the Mi Home app.
# - "dreame_segment": the Dreame `start-clean` action with the segment work
#   mode and a `{"selects": [[room, repeat, fan, water, order], ...]}` room
#   selection (X20+). The spec's own `start-room-sweep` is acknowledged but
#   ignored by the firmware.
RoomCleanStrategy = Literal["direct", "config_then_custom", "dreame_segment"]

# Format of the cloud map blob, which picks the xiaomi-vacuum-sdk decoder and
# where the room list comes from.
# - "xiaomi": encrypted Xiaomi JSON payload; rooms come from the
#   room-information property.
# - "dreame": Dreame frame (pixel grid plus JSON trailer); rooms are decoded
#   from the map's segment metadata (X20+).
MapFormat = Literal["xiaomi", "dreame"]

#: Task-status value meaning "no job open". Dreame-built models publish a
#: task-status property (0 completed, 1 auto clean, 2 zone, 3 room, 6+ the
#: matching paused states, ...) that, unlike the status, stays non-zero for the
#: whole job: through mid-job mop washes, recharges and the drive back.
TASK_STATUS_COMPLETED = 0


#: Maps each optional :class:`Capability` to the :class:`EntityKey` it gates.
_CAPABILITY_ENTITIES: dict[Capability, EntityKey] = {
    Capability.DUST_ARREST: EntityKey.DUST_ARREST_BUTTON,
    Capability.SWEEP_ROUTE: EntityKey.SWEEP_ROUTE_SELECT,
    Capability.OBSTACLE_AVOIDANCE: EntityKey.OBSTACLE_AVOIDANCE_SELECT,
}

#: Entities every supported vacuum exposes regardless of capabilities.
#: Includes the platforms whose creation is otherwise unconditional
#: (vacuum entity, sensors, binary sensors) so the entity-key
#: registry stays the single source of truth for what a model exposes.
_BASE_ENTITIES: frozenset[EntityKey] = frozenset(
    {
        EntityKey.VACUUM,
        EntityKey.BATTERY_SENSOR,
        EntityKey.STATUS_SENSOR,
        EntityKey.ERROR_SENSOR,
        EntityKey.ERROR_CODE_SENSOR,
        EntityKey.MOP_LIFE_SENSOR,
        EntityKey.MAIN_BRUSH_LIFE_SENSOR,
        EntityKey.SIDE_BRUSH_LIFE_SENSOR,
        EntityKey.FILTER_LIFE_SENSOR,
        EntityKey.BATTERY_CHARGING_SENSOR,
        EntityKey.CLEANING_SENSOR,
    }
)

#: Entities backed by one property, created only when the model maps it. The
#: Xiaomi in-house models map all of them; the X20+ packs its sweep/mop mode
#: into a Dreame clean-setting bitfield and publishes no clean-times property.
_PROPERTY_ENTITIES: dict[Property, EntityKey] = {
    Property.MAP_OBJ_NAME: EntityKey.MAP_IMAGE,
    Property.MOP_STATUS: EntityKey.MOP_PAD_SENSOR,
    Property.SWEEP_MOP_TYPE: EntityKey.SWEEP_MOP_TYPE_SELECT,
    Property.CLEAN_TIMES: EntityKey.CLEAN_TIMES_SELECT,
    Property.MOP_WATER_LEVEL: EntityKey.MOP_WATER_LEVEL_SELECT,
    Property.MAIN_BRUSH_TIME_LEFT: EntityKey.MAIN_BRUSH_TIME_LEFT_SENSOR,
    Property.SIDE_BRUSH_TIME_LEFT: EntityKey.SIDE_BRUSH_TIME_LEFT_SENSOR,
    Property.FILTER_TIME_LEFT: EntityKey.FILTER_TIME_LEFT_SENSOR,
    Property.MOP_TIME_LEFT: EntityKey.MOP_TIME_LEFT_SENSOR,
    Property.DRYING_TIME_LEFT: EntityKey.DRYING_TIME_LEFT_SENSOR,
    Property.TOTAL_CLEAN_TIME: EntityKey.TOTAL_CLEAN_TIME_SENSOR,
    Property.TOTAL_CLEAN_COUNT: EntityKey.TOTAL_CLEAN_COUNT_SENSOR,
    Property.TOTAL_CLEAN_AREA: EntityKey.TOTAL_CLEAN_AREA_SENSOR,
    Property.CHILD_LOCK: EntityKey.CHILD_LOCK_SWITCH,
    Property.CARPET_BOOST: EntityKey.CARPET_BOOST_SWITCH,
    Property.RESUME_AFTER_CHARGE: EntityKey.RESUME_AFTER_CHARGE_SWITCH,
    Property.DO_NOT_DISTURB: EntityKey.DO_NOT_DISTURB_SWITCH,
    Property.VOLUME: EntityKey.VOLUME_NUMBER,
}

#: Button entities backed by one optional :class:`ModelActions` field, created
#: only when the model defines that action.
_ACTION_ENTITIES: dict[str, EntityKey] = {
    "start_mop_wash": EntityKey.START_MOP_WASH_BUTTON,
    "stop_mop_wash": EntityKey.STOP_MOP_WASH_BUTTON,
    "start_dry": EntityKey.START_DRY_BUTTON,
    "stop_dry": EntityKey.STOP_DRY_BUTTON,
    "reset_main_brush": EntityKey.RESET_MAIN_BRUSH_BUTTON,
    "reset_side_brush": EntityKey.RESET_SIDE_BRUSH_BUTTON,
    "reset_filter": EntityKey.RESET_FILTER_BUTTON,
    "reset_mop": EntityKey.RESET_MOP_BUTTON,
}

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
    "property_masks",
)


@dataclass(frozen=True)
class ModelSpec:
    """Everything model-specific the integration needs at runtime."""

    model: str
    name: str
    property_mapping: dict[Property, MiotPropertyAddress]
    actions: ModelActions
    status: dict[int, StatusSlug]
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
    # Fault codes this model publishes permanently for hardware it does not
    # have. The firmware image is shared across a product family, so a unit
    # sold with a reduced dock still runs the station checks and reports their
    # failure forever; the Mi Home app knows the dock type and hides them. They
    # are dropped before the fault reaches the entities, otherwise the vacuum
    # would sit in ERROR for its whole life (see S40 Pro / code 100027).
    ignored_fault_codes: frozenset[int] = frozenset()
    # Fault codes that are routine maintenance notices rather than faults: the
    # robot publishes them while the user empties the dust bin or refills the
    # water tank, and clears them once the part is back. They still reach the
    # Error / Error code sensors but do not force VacuumActivity.ERROR, the way
    # other vacuum integrations treat dismissable warnings.
    notice_fault_codes: frozenset[int] = frozenset()
    # The custom cleanings list is read on demand, not polled: it grows with
    # every cleaning saved in Mi Home and would push the batched poll reply past
    # the single-datagram limit.
    user_define_sweep_config: MiotPropertyAddress | None = None
    map_format: MapFormat = "xiaomi"
    # Properties that live in some bits of a packed device value: the mask
    # picks the bits (e.g. the X20+ cleaning mode in the low two bits of its
    # clean-setting). Reads expose only those bits, shifted down; writes keep
    # every other bit as the device reports it.
    property_masks: dict[Property, int] = field(default_factory=dict)

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
        """Status code → HA activity."""
        return {
            code: STATUS_MEANINGS[slug].activity for code, slug in self.status.items()
        }

    @property
    def status_slugs(self) -> dict[int, str]:
        """Status code → translation slug."""
        return {code: str(slug) for code, slug in self.status.items()}

    @property
    def idle_statuses(self) -> frozenset[int]:
        """Status codes that count as parked/idle (a fresh start is safe)."""
        return frozenset(
            code for code, slug in self.status.items() if STATUS_MEANINGS[slug].is_idle
        )

    @property
    def cleaning_job_signals(self) -> dict[int, CleaningJobSignal]:
        """Status code → what it reveals about the cleaning job."""
        return {
            code: STATUS_MEANINGS[slug].cleaning_job
            for code, slug in self.status.items()
        }

    def status_code_for(self, activity: VacuumActivity) -> int:
        """
        Return the status code an optimistic UI patch reports for ``activity``.

        A command reports the same activity the device will confirm on the next
        poll, without the platform hard-coding per-model status codes: the code
        of the activity's canonical slug, else the first code with that activity.
        """
        canonical = CANONICAL_STATUSES.get(activity)
        matches = [
            code
            for code, slug in self.status.items()
            if STATUS_MEANINGS[slug].activity is activity
        ]
        for code in matches:
            if self.status[code] is canonical:
                return code
        if matches:
            return matches[0]
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
        """Entities to create: base set, capability-gated and property-backed ones."""
        keys = set(_BASE_ENTITIES)
        for cap in self.capabilities:
            if (key := _CAPABILITY_ENTITIES.get(cap)) is not None:
                keys.add(key)
        keys.update(
            key
            for prop, key in _PROPERTY_ENTITIES.items()
            if prop in self.property_mapping
        )
        keys.update(
            key
            for action, key in _ACTION_ENTITIES.items()
            if getattr(self.actions, action) is not None
        )
        return frozenset(keys)

    @property
    def supports_room_clean(self) -> bool:
        """Whether the model has the actions its room-clean strategy needs."""
        actions = self.actions
        if self.room_clean_strategy == "direct":
            return actions.start_room_sweep is not None
        if self.room_clean_strategy == "config_then_custom":
            return (
                actions.set_room_clean_configs is not None
                and actions.start_custom_sweep is not None
            )
        return actions.start_segment_clean is not None

    def cleaning_job_signal(
        self, status: int | None, task_status: int | None = None
    ) -> CleaningJobSignal:
        """
        Return what the polled state reveals about the cleaning job.

        A model that maps :attr:`Property.TASK_STATUS` decides from it alone: it
        is the one value that stays set for the whole job, while the status
        repeats codes mid-job and after it (charging, mop washing). Other models,
        and a task status not polled yet, fall back to the status table.
        """
        if Property.TASK_STATUS in self.property_mapping and isinstance(
            task_status, int
        ):
            if task_status == TASK_STATUS_COMPLETED:
                return CleaningJobSignal.FINISHED
            return CleaningJobSignal.IN_PROGRESS
        if status is None or (signal := self.cleaning_job_signals.get(status)) is None:
            return CleaningJobSignal.INCONCLUSIVE
        return signal

    def is_idle(self, status: int | None, task_status: int | None = None) -> bool:
        """
        Whether a fresh clean is safe: parked/idle with no job left to resume.

        The task status vetoes an idle status while a job is still open, e.g. the
        X20+ charging mid-job reports the same status as charging after it.
        """
        if status not in self.idle_statuses:
            return False
        return (
            self.cleaning_job_signal(status, task_status)
            is not CleaningJobSignal.IN_PROGRESS
        )

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
