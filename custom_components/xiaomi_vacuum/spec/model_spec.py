"""Everything the integration needs to know about one vacuum model."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING

from .cleaning_job_signal import CleaningJobSignal
from .entity_requirements import ACTION_ENTITIES, BASE_ENTITIES, PROPERTY_ENTITIES
from .fault_reading import FaultIdsReading, PlainFaultReading
from .map_format import MapFormat, XiaomiMapFormat
from .property import Property
from .send_commands import SEND_COMMAND_ACTIONS
from .status_catalog import CANONICAL_STATUSES, STATUS_MEANINGS

if TYPE_CHECKING:
    from homeassistant.components.vacuum.const import VacuumActivity

    from ..data import VacuumState  # noqa: TID252
    from .addresses import MiotActionAddress, MiotPropertyBinding
    from .entity_key import EntityKey
    from .fault_reading import FaultReading
    from .model_actions import ModelActions
    from .room_cleaning import RoomCleaning
    from .status_slug import StatusSlug

_XIAOMI_MAP_FORMAT = XiaomiMapFormat()

#: Task-status value meaning "no job open". Dreame-built models publish a
#: task-status property (0 completed, 1 auto clean, 2 zone, 3 room, 6+ the
#: matching paused states, ...) that, unlike the status, stays non-zero for the
#: whole job: through mid-job mop washes, recharges and the drive back.
TASK_STATUS_COMPLETED = 0


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
    "sweep_routes",
    "obstacle_avoidances",
)


@dataclass(frozen=True)
class ModelSpec:
    """Everything model-specific the integration needs at runtime."""

    model: str
    name: str
    property_mapping: dict[Property, MiotPropertyBinding]
    actions: ModelActions
    status: dict[int, StatusSlug]
    # Value tables of the matching properties, empty when the model does not
    # map the property. Kept on the spec — not module-level — so a vacuum
    # publishing a different table gets its own instead of the X20 Max's.
    fan_speeds: dict[str, int] = field(default_factory=dict)
    sweep_mop_types: dict[str, int] = field(default_factory=dict)
    clean_times: dict[str, int] = field(default_factory=dict)
    mop_water_levels: dict[str, int] = field(default_factory=dict)
    charging_state_slugs: dict[int, str] = field(default_factory=dict)
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
    room_cleaning: RoomCleaning | None = None
    map_format: MapFormat = _XIAOMI_MAP_FORMAT

    def __post_init__(self) -> None:
        """Wrap the mutable dict fields in read-only views."""
        # ``frozen=True`` only blocks attribute reassignment; the dict fields are
        # still mutable and would otherwise be shared across instances (and with
        # ``MiotDevice`` via ``property_mapping``). ``object.__setattr__`` is the
        # sanctioned way to normalise fields inside a frozen dataclass.
        for name in MAPPING_FIELDS:
            object.__setattr__(self, name, MappingProxyType(getattr(self, name)))

    @property
    def property_masks(self) -> dict[Property, int]:
        """Property → the bits of its packed device value it owns."""
        return {
            name: binding["mask"]
            for name, binding in self.property_mapping.items()
            if "mask" in binding
        }

    @property
    def polled_properties(self) -> dict[Property, MiotPropertyBinding]:
        """The mapped properties read by the periodic poll."""
        return {
            name: binding
            for name, binding in self.property_mapping.items()
            if binding.get("polled", True)
        }

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
    def entities(self) -> frozenset[EntityKey]:
        """Entities to create: the base set plus those whose requirement is met."""
        keys = set(BASE_ENTITIES)
        keys.update(
            key
            for name, key in PROPERTY_ENTITIES.items()
            if name in self.property_mapping
        )
        keys.update(
            key
            for action, key in ACTION_ENTITIES.items()
            if getattr(self.actions, action) is not None
        )
        return frozenset(keys)

    @property
    def send_commands(self) -> dict[str, MiotActionAddress]:
        """The ``send_command`` names this model accepts, with their actions."""
        commands: dict[str, MiotActionAddress] = {}
        for name in SEND_COMMAND_ACTIONS:
            action: MiotActionAddress | None = getattr(self.actions, name)
            if action is not None:
                commands[name] = action
        return commands

    @property
    def fault_reading(self) -> FaultReading:
        """How the live fault is read: the fault-ids list when mapped, else plain."""
        if Property.FAULT_IDS in self.property_mapping:
            return FaultIdsReading()
        return PlainFaultReading()

    def live_fault_code(self, data: VacuumState) -> int | None:
        """Return the live fault code of a polled state, phantom faults dropped."""
        return self.fault_reading.live_code(
            data, self.ignored_fault_codes, self.notice_fault_codes
        )

    @property
    def supports_room_clean(self) -> bool:
        """Whether the model has a room-cleaning flow."""
        return self.room_cleaning is not None

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
