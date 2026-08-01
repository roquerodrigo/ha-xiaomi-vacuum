"""Local MIoT client for xiaomi_vacuum."""

from __future__ import annotations

import json
from functools import partial
from typing import TYPE_CHECKING, cast

from miio import DeviceException, MiotDevice
from miio.exceptions import DeviceError

from ..cloud.errors import XiaomiCloudError  # noqa: TID252
from ..const import LOGGER  # noqa: TID252
from ..spec import Property  # noqa: TID252
from .errors import (
    XiaomiVacuumApiClientCommunicationError,
    XiaomiVacuumApiClientError,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant

    from ..cloud import XiaomiCloud  # noqa: TID252
    from ..data import DeviceInfoLike, VacuumState  # noqa: TID252
    from ..spec import ModelSpec  # noqa: TID252


class XiaomiVacuumApiClient:
    """Local MIoT client wrapping python-miio's MiotDevice for one model."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        token: str,
        spec: ModelSpec,
    ) -> None:
        """Initialize with the model's spec (property + action mapping)."""
        self._hass = hass
        self._spec = spec
        # Xiaomi vacuums routinely take >5 s to ack action commands (start /
        # pause / room-sweep) — the device is busy spinning up and misses the
        # default miio read window, surfacing as `-9999 user ack timeout`.
        # 10 s is a forgiving middle ground that avoids most spurious failures
        # without making a genuinely-offline device feel unresponsive.
        self._device = MiotDevice(
            ip=host,
            token=token,
            # ``property_mapping`` is a ``MappingProxyType`` (read-only view) so the
            # spec's shared state can't be mutated through ``MiotDevice``.
            # ``python-miio`` only reads the mapping (``.items()`` in
            # ``get_properties_for_mapping``, ``[key]`` in ``call_action_by`` /
            # ``set_property_by``) — verified against miio 0.5.12 — so a read-only
            # view is safe to hand it. The ``type: ignore`` is for the key/value
            # types (StrEnum + TypedDict vs miio's plain ``dict[str, Any]``), not
            # for the mapping vs ``mappingproxy`` distinction.
            mapping=spec.property_mapping,  # type: ignore[arg-type]
            timeout=10,
        )
        # Cloud client, set by the integration after the cloud session resolves.
        # When present, multi-step flows that local UDP mishandles (e.g. the S20+
        # room-clean) are routed through the cloud for reliability — matching
        # what the Mi Home app does.
        self._cloud: XiaomiCloud | None = None

    def set_cloud(self, cloud: XiaomiCloud | None) -> None:
        """Attach (or detach) the Xiaomi cloud client for cloud-routed actions."""
        self._cloud = cloud

    async def _run[T, **P](
        self, func: Callable[P, T], *args: P.args, **kwargs: P.kwargs
    ) -> T:
        """Run a sync python-miio call in the executor, normalizing errors."""
        try:
            return await self._hass.async_add_executor_job(
                partial(func, *args, **kwargs)
            )
        except DeviceException as exception:
            msg = f"Device error: {exception}"
            raise XiaomiVacuumApiClientCommunicationError(msg) from exception
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Unexpected error: {exception}"
            raise XiaomiVacuumApiClientError(msg) from exception

    async def _run_action[T, **P](
        self, func: Callable[P, T], *args: P.args, **kwargs: P.kwargs
    ) -> T:
        """
        Run an MIoT action, tolerating the flaky ``-9999 user ack timeout``.

        Xiaomi vacuums often accept a command (start / pause / room-sweep) and
        then never send the ack because the robot is already busy moving. The
        command usually *did* reach the device, so we treat an ack-timeout as
        accepted instead of bubbling a communication error up to Home Assistant:
        the optimistic UI patch + the scheduled ~5 s refresh will reconcile the
        real state. Any other device error still raises.
        """
        try:
            return await self._run(func, *args, **kwargs)
        except XiaomiVacuumApiClientCommunicationError as exception:
            if _is_ack_timeout(exception):
                LOGGER.warning(
                    "Device did not ack the action in time (-9999); assuming it "
                    "was accepted. State will be confirmed on the next refresh."
                )
                return None  # type: ignore[return-value]
            raise

    async def async_get_info(self) -> DeviceInfoLike:
        """Handshake — returns python-miio DeviceInfo (model, mac, fw)."""
        return cast("DeviceInfoLike", await self._run(self._device.info))

    async def async_get_state(self) -> VacuumState:
        """Read all mapped properties (indexed by siid+piid)."""
        rows = await self._run(self._device.get_properties_for_mapping)
        LOGGER.debug("Raw MIoT rows: %s", rows)
        by_key = {
            (r["siid"], r["piid"]): r["value"] for r in rows if r.get("code") == 0
        }
        mapping = self._spec.property_mapping
        parsed = {
            name: by_key.get((p["siid"], p["piid"])) for name, p in mapping.items()
        }
        LOGGER.debug("Parsed state: %s", parsed)
        return cast("VacuumState", parsed)

    async def async_start(self) -> None:
        """Start sweeping."""
        a = self._spec.actions.start_sweep
        await self._run_action(self._device.call_action_by, a["siid"], a["aiid"])

    async def async_continue(self) -> None:
        """Resume a paused job (keeps the current task instead of restarting)."""
        a = self._spec.actions.continue_sweep
        await self._run_action(self._device.call_action_by, a["siid"], a["aiid"])

    async def async_pause(self) -> None:
        """Pause current job."""
        a = self._spec.actions.pause_sweeping
        await self._run_action(self._device.call_action_by, a["siid"], a["aiid"])

    async def async_stop(self) -> None:
        """Stop current job."""
        a = self._spec.actions.stop_sweeping
        await self._run_action(self._device.call_action_by, a["siid"], a["aiid"])

    async def async_return_home(self) -> None:
        """Stop and return to dock."""
        a = self._spec.actions.return_home
        await self._run_action(self._device.call_action_by, a["siid"], a["aiid"])

    async def async_locate(self) -> None:
        """Identify (beep + light)."""
        a = self._spec.actions.identify
        await self._run_action(self._device.call_action_by, a["siid"], a["aiid"])

    async def async_call_action(self, siid: int, aiid: int) -> None:
        """Invoke an arbitrary MIoT action (backs the send_command service)."""
        await self._run_action(self._device.call_action_by, siid, aiid)

    async def async_start_dust_arrest(self) -> None:
        """Trigger dock to empty the vacuum's dust bin (X20 Max only)."""
        a = self._spec.actions.start_dust_arrest
        if a is None:
            msg = "This model has no dust-arrest dock"
            raise XiaomiVacuumApiClientError(msg)
        await self._run_action(self._device.call_action_by, a["siid"], a["aiid"])

    async def async_set_fan_speed(self, fan_speed: str) -> None:
        """Set fan speed by label (Silent/Basic/Strong/Full Speed)."""
        speeds = self._spec.fan_speeds
        if fan_speed not in speeds:
            msg = f"Unknown fan speed: {fan_speed}"
            raise XiaomiVacuumApiClientError(msg)
        prop = self._spec.property_mapping[Property.FAN_SPEED]
        await self._run(
            self._device.set_property_by,
            prop["siid"],
            prop["piid"],
            speeds[fan_speed],
        )

    async def async_set_sweep_mop_type(self, mode: str) -> None:
        """Set sweep/mop mode (sweep / mop / sweep_mop / sweep_before_mopping)."""
        types = self._spec.sweep_mop_types
        if mode not in types:
            msg = f"Unknown sweep_mop_type: {mode}"
            raise XiaomiVacuumApiClientError(msg)
        await self.async_set_property("sweep_mop_type", types[mode])

    async def async_set_property(self, name: str, value: int) -> None:
        """Set a MIoT property by mapping name (raw integer value)."""
        prop = self._spec.property_mapping.get(cast("Property", name))
        if prop is None:
            msg = f"Unknown property: {name}"
            raise XiaomiVacuumApiClientError(msg)
        await self._run(self._device.set_property_by, prop["siid"], prop["piid"], value)

    async def async_clean_segments(
        self, segment_ids: list[str], room_information: str | None = None
    ) -> None:
        """
        Start cleaning specific rooms by their MIoT room IDs.

        Two strategies, picked by the active model's spec:

        * ``direct`` (X20 Max) — fire ``start-vacuum-room-sweep`` with the room
          ids as a comma-separated string.
        * ``config_then_custom`` (S20+) — captured from the Mi Home app: rebuild
          the room config from ``room_information`` with the target rooms'
          ``on`` flag set to True (others False), push it via
          ``set-room-clean-configs``, then fire ``start-custom-sweep``. The
          spec's ``start-vacuum-room-sweep`` (aiid 13) exists but the robot
          ignores it and returns to the dock.
        """
        strategy = self._spec.room_clean_strategy
        actions = self._spec.actions
        if strategy == "direct":
            if actions.start_room_sweep is None:
                msg = "direct room-clean strategy but no start_room_sweep action"
                raise XiaomiVacuumApiClientError(msg)
            a = actions.start_room_sweep
            payload = [
                {
                    "piid": a["in_piid"],
                    "value": ",".join(str(r) for r in segment_ids),
                }
            ]
            LOGGER.debug("Calling start-vacuum-room-sweep with payload: %s", payload)
            await self._run_action(
                self._device.call_action_by, a["siid"], a["aiid"], payload
            )
            return

        # config_then_custom (S20+)
        if actions.set_room_clean_configs is None or actions.start_custom_sweep is None:
            msg = (
                "config_then_custom room-clean strategy requires both "
                "set_room_clean_configs and start_custom_sweep actions"
            )
            raise XiaomiVacuumApiClientError(msg)
        config = _build_room_clean_config(room_information, segment_ids)
        if not config:
            msg = (
                "Cannot start room clean: the device published no room "
                "information. Configure rooms in the Mi Home app first."
            )
            raise XiaomiVacuumApiClientError(msg)
        set_action = actions.set_room_clean_configs
        config_payload = [json.dumps({"room_attrs": config})]
        LOGGER.debug(
            "Calling set-room-clean-configs (%s/%s) with %d room(s), cleaning %d",
            set_action["siid"],
            set_action["aiid"],
            len(config),
            sum(1 for r in config if r.get("on")),
        )
        await self._call_action_cloud_or_local(
            set_action["siid"], set_action["aiid"], config_payload
        )
        start_action = actions.start_custom_sweep
        LOGGER.debug(
            "Calling start-custom-sweep (%s/%s)",
            start_action["siid"],
            start_action["aiid"],
        )
        await self._call_action_cloud_or_local(
            start_action["siid"], start_action["aiid"], []
        )

    async def _call_action_cloud_or_local(
        self, siid: int, aiid: int, params: list[str]
    ) -> None:
        """
        Invoke a MIoT action, preferring the cloud when a session is available.

        The cloud path (reliable TCP) is used for actions that local UDP
        mishandles on flaky Wi-Fi — multi-step flows like the S20+ room-clean,
        where a single ``-9999`` on the first step would otherwise leave the
        second step running uselessly. When no cloud session is configured we
        fall back to the local miio path (with its ack-timeout tolerance).
        """
        if self._cloud is not None:
            try:
                result = await self._cloud.async_call_action(siid, aiid, params)
            except XiaomiCloudError as exc:
                msg = f"Cloud action {siid}/{aiid} failed: {exc}"
                raise XiaomiVacuumApiClientError(msg) from exc
            # ``async_call_action`` returns ``None`` when the cloud client has no
            # active session or no resolved device — i.e. the cloud transport is
            # unavailable, not that the action succeeded. Treating that as success
            # would let a room clean silently no-op while the optimistic UI has
            # already reported it started. Fall through to the local path so the
            # command still gets a chance to reach the device, mirroring the
            # session-absent branch below.
            if result is None:
                LOGGER.debug(
                    "No cloud session for action %s/%s; using local transport",
                    siid,
                    aiid,
                )
            else:
                LOGGER.debug("Cloud action %s/%s response: %s", siid, aiid, result)
                if isinstance(result.get("code"), int):
                    code = result["code"]
                    if code != 0:
                        msg = (
                            f"Cloud action {siid}/{aiid} rejected by device: "
                            f"code={code} message={result.get('message')!r}"
                        )
                        raise XiaomiVacuumApiClientError(msg)
                return
        await self._run_action(self._device.call_action_by, siid, aiid, params)


_ACK_TIMEOUT_CODE = -9999


def _is_ack_timeout(exception: BaseException) -> bool:
    """
    Return True if the error chain carries a ``-9999 user ack timeout`` from miio.

    python-miio exhausts its retries and raises a generic
    ``DeviceException("Unable to recover failed command")`` whose ``__cause__``
    is the last ``RecoverableError`` — a ``DeviceError`` subclass carrying the
    original ``code``/``message``. We walk that chain rather than grepping the
    message so the check survives wording changes across miio versions.
    """
    cause: BaseException | None = exception
    while cause is not None:
        if isinstance(cause, DeviceError) and cause.code == _ACK_TIMEOUT_CODE:
            return True
        cause = cause.__cause__ or cause.__context__
    return False


# Columns published by the S20+ `room-info` property (SIID 6 / piid 10) and
# accepted by `set-room-clean-configs` (SIID 2 / aiid 10). Order matters: the
# device publishes a table `room_attrs` whose first row is exactly this header.
_ROOM_ATTR_HEADERS = (
    "id",
    "room_name",
    "fan_level",
    "water_level",
    "clean_mode",
    "clean_times",
    "mop_mode",
    "on",
)


def _build_room_clean_config(
    room_information: str | None, segment_ids: list[str]
) -> list[dict[str, object]]:
    """
    Build the S20+ ``set-room-clean-configs`` payload.

    Reads the current room config from ``room_information`` (the device's
    table-shaped ``room_attrs`` JSON), converts it to the object-array write
    format the action expects, and flips the ``on`` flag to True for every
    requested room id (False for the rest). Returns an empty list when the
    device published no rooms (caller should refuse to start in that case).

    The order of selected rooms is preserved from ``segment_ids``: the Mi Home
    app stores the cleaning sequence as the position of each room in
    ``room_attrs``, so we emit the requested rooms first (in the order the
    caller asked for), followed by the unselected ones in their original
    relative order. A ``clean_area`` call with ``[kitchen, living_room]`` thus
    cleans kitchen before living_room.
    """
    if not room_information:
        return []
    try:
        data = json.loads(room_information)
    except ValueError, TypeError:
        return []
    matrix = data.get("room_attrs") if isinstance(data, dict) else None
    if not isinstance(matrix, list) or not matrix:
        return []
    header = matrix[0] if isinstance(matrix[0], list) else list(_ROOM_ATTR_HEADERS)
    # Normalise header cells to lower-case, matching ``_rows_to_attrs`` in
    # ``vacuum/cleaner.py``: both parsers read the same ``room_attrs`` payload,
    # so a device publishing ``Id`` / ``Room_Name`` instead of the lower-case
    # spelling resolves identically in both places. Without this the per-room
    # ``id`` lookup below fails on every row and the config comes back empty.
    header = [str(c).casefold() if c is not None else "" for c in header]
    # Requested sequence as an ordered lookup: position decides emit order.
    wanted_order = [str(s) for s in segment_ids]
    wanted = set(wanted_order)
    selected: list[dict[str, object]] = []
    others: list[dict[str, object]] = []
    for row in matrix[1:]:
        if not isinstance(row, list):
            continue
        room = dict(zip(header, row, strict=False))
        room_id = room.get("id")
        if room_id is None:
            continue
        room_id_str = str(room_id)
        room["on"] = room_id_str in wanted
        if room["on"]:
            selected.append(room)
        else:
            others.append(room)
    # Reorder selected rooms to match the requested sequence (stable for any
    # ids the device knows but the caller didn't list, which shouldn't happen).
    selected.sort(key=lambda r: _ordered_index(str(r.get("id")), wanted_order))
    return selected + others


def _ordered_index(room_id: str, wanted_order: list[str]) -> int:
    """Position of ``room_id`` in ``wanted_order``, or a large sentinel if absent."""
    try:
        return wanted_order.index(room_id)
    except ValueError:
        return len(wanted_order)
