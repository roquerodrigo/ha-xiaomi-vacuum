"""Local MIoT client for xiaomi_vacuum."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from xiaomi_vacuum_sdk import (
    ActionAddress,
    MiotAckTimeoutError,
    MiotClient,
    MiotError,
    PropertyAddress,
    PropertyValue,
)

from ..cloud.errors import (  # noqa: TID252
    XiaomiCloudAuthError,
    XiaomiCloudConnectionError,
    XiaomiCloudError,
)
from ..const import LOGGER  # noqa: TID252
from ..spec import Property  # noqa: TID252
from ..spec.room_cleaning import RoomCleaningError  # noqa: TID252
from .custom_cleaning import CustomCleaning
from .errors import (
    XiaomiVacuumApiClientCommunicationError,
    XiaomiVacuumApiClientError,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Sequence

    from ..cloud import XiaomiCloud  # noqa: TID252
    from ..data import (  # noqa: TID252
        DeviceInfoLike,
        JsonValue,
        VacuumState,
    )
    from ..spec import ModelSpec  # noqa: TID252
    from ..spec.addresses import MiotActionAddress  # noqa: TID252
    from .cleaning_zone import CleaningZone

# Xiaomi vacuums routinely take >5 s to ack action commands (start / pause /
# room-sweep) — the device is busy spinning up and misses the default read
# window, surfacing as `-9999 user ack timeout`. 10 s is a forgiving middle
# ground that avoids most spurious failures without making a genuinely-offline
# device feel unresponsive.
_DEVICE_TIMEOUT_SECONDS = 10.0

# The vacuums silently drop any reply that does not fit in a single UDP
# datagram. The room list grows with the number and names of the rooms (non-ASCII
# names are escaped), so batching it with other properties can push the reply
# past that limit and leave every poll unanswered.
_STANDALONE_PROPERTIES = frozenset({Property.ROOM_INFORMATION})


class XiaomiVacuumApiClient:
    """Local MIoT client backed by ``xiaomi-vacuum-sdk`` for one model."""

    def __init__(self, host: str, token: str, spec: ModelSpec) -> None:
        """Initialize with the model's spec (property + action mapping)."""
        self._spec = spec
        self._client = MiotClient(host, token, timeout=_DEVICE_TIMEOUT_SECONDS)
        self._properties: dict[str, PropertyAddress] = {
            name: PropertyAddress(siid=address["siid"], piid=address["piid"])
            for name, address in spec.property_mapping.items()
        }
        self._property_requests = _group_property_requests(
            {name: self._properties[name] for name in spec.polled_properties}
        )
        # Cloud client, set by the integration after the cloud session resolves.
        # When present, multi-step flows that local UDP mishandles (e.g. the S20+
        # room-clean) are routed through the cloud for reliability — matching
        # what the Mi Home app does.
        self._cloud: XiaomiCloud | None = None

    def set_cloud(self, cloud: XiaomiCloud | None) -> None:
        """Attach (or detach) the Xiaomi cloud client for cloud-routed actions."""
        self._cloud = cloud

    async def _run[T](self, operation: Awaitable[T]) -> T:
        """Await one SDK call, normalizing errors to the integration types."""
        try:
            return await operation
        except MiotError as exception:
            msg = f"Device error: {exception}"
            raise XiaomiVacuumApiClientCommunicationError(msg) from exception
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Unexpected error: {exception}"
            raise XiaomiVacuumApiClientError(msg) from exception

    async def _run_action(self, operation: Awaitable[JsonValue]) -> None:
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
            await operation
        except MiotAckTimeoutError:
            LOGGER.warning(
                "Device did not ack the action in time (-9999); assuming it "
                "was accepted. State will be confirmed on the next refresh."
            )
        except MiotError as exception:
            msg = f"Device error: {exception}"
            raise XiaomiVacuumApiClientCommunicationError(msg) from exception
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Unexpected error: {exception}"
            raise XiaomiVacuumApiClientError(msg) from exception

    async def async_get_info(self) -> DeviceInfoLike:
        """Handshake — returns the device identity (model, mac, fw)."""
        return await self._run(self._client.info())

    async def async_get_state(self) -> VacuumState:
        """Read all mapped properties, keyed by the spec's property names."""
        values: dict[str, PropertyValue] = {}
        for properties in self._property_requests:
            values |= await self._run(self._client.get_properties(properties))
        values = self._unmask(values)
        LOGGER.debug("Parsed state: %s", values)
        return cast("VacuumState", values)

    def _unmask(self, values: dict[str, PropertyValue]) -> dict[str, PropertyValue]:
        """Keep only the bits a masked property owns, shifted down."""
        for name, mask in self._spec.property_masks.items():
            raw = values.get(name)
            if isinstance(raw, int) and not isinstance(raw, bool):
                values[name] = (raw & mask) >> _mask_shift(mask)
        return values

    async def async_start(self) -> None:
        """Start sweeping."""
        await self._run_action(
            self._client.call_action(_address(self._spec.actions.start_sweep))
        )

    async def async_continue(self) -> None:
        """Resume a paused job (keeps the current task instead of restarting)."""
        await self._run_action(
            self._client.call_action(_address(self._spec.actions.continue_sweep))
        )

    async def async_pause(self) -> None:
        """Pause current job."""
        await self._run_action(
            self._client.call_action(_address(self._spec.actions.pause_sweeping))
        )

    async def async_stop(self) -> None:
        """Stop current job."""
        await self._run_action(
            self._client.call_action(_address(self._spec.actions.stop_sweeping))
        )

    async def async_return_home(self) -> None:
        """Stop and return to dock."""
        await self._run_action(
            self._client.call_action(_address(self._spec.actions.return_home))
        )

    async def async_locate(self) -> None:
        """Identify (beep + light)."""
        await self._run_action(
            self._client.call_action(_address(self._spec.actions.identify))
        )

    async def async_run_action(self, action: MiotActionAddress) -> None:
        """Invoke a parameterless spec action (dock and consumable buttons)."""
        await self._run_action(self._client.call_action(_address(action)))

    async def async_call_action(self, siid: int, aiid: int) -> None:
        """Invoke an arbitrary MIoT action (backs the send_command service)."""
        await self._run_action(
            self._client.call_action(ActionAddress(siid=siid, aiid=aiid))
        )

    async def async_set_fan_speed(self, fan_speed: str) -> None:
        """Set fan speed by label (Silent/Basic/Strong/Full Speed)."""
        speeds = self._spec.fan_speeds
        if fan_speed not in speeds:
            msg = f"Unknown fan speed: {fan_speed}"
            raise XiaomiVacuumApiClientError(msg)
        await self.async_set_property(Property.FAN_SPEED, value=speeds[fan_speed])

    async def async_set_sweep_mop_type(self, mode: str) -> None:
        """Set sweep/mop mode (sweep / mop / sweep_mop / sweep_before_mopping)."""
        types = self._spec.sweep_mop_types
        if mode not in types:
            msg = f"Unknown sweep_mop_type: {mode}"
            raise XiaomiVacuumApiClientError(msg)
        await self.async_set_property(Property.SWEEP_MOP_TYPE, value=types[mode])

    async def async_set_property(self, name: Property, *, value: bool | int) -> None:
        """
        Set a MIoT property by mapping name, encoded as its binding says.

        A ``boolean`` property is written as a bool, any other as an integer. A
        masked property only owns some bits of the device value, so the current
        value is read first and the other bits are written back unchanged.
        """
        address = self._properties.get(name)
        if address is None:
            msg = f"Unknown property: {name}"
            raise XiaomiVacuumApiClientError(msg)
        binding = self._spec.property_mapping[name]
        value = bool(value) if binding.get("boolean") else int(value)
        mask = binding.get("mask")
        if mask is not None:
            current = (
                await self._run(self._client.get_properties({name: address}))
            ).get(name)
            if not isinstance(current, int) or isinstance(current, bool):
                msg = f"Failed to set {name}: could not read its current value"
                raise XiaomiVacuumApiClientError(msg)
            value = (current & ~mask) | ((int(value) << _mask_shift(mask)) & mask)
        await self._run(self._client.set_property(address, value))

    async def async_clean_segments(
        self, segment_ids: list[str], room_information: str | None = None
    ) -> None:
        """Start cleaning specific rooms with the model's room-cleaning flow."""
        room_cleaning = self._spec.room_cleaning
        if room_cleaning is None:
            msg = "Failed to clean rooms: this model has no room cleaning"
            raise XiaomiVacuumApiClientError(msg)
        try:
            await room_cleaning.async_start(self, segment_ids, room_information)
        except RoomCleaningError as exception:
            raise XiaomiVacuumApiClientError(str(exception)) from exception

    async def async_call_action_with_params(
        self, action: MiotActionAddress, params: list[JsonValue]
    ) -> None:
        """Invoke an action with input params, tolerating the device's late acks."""
        await self._run_action(self._client.call_action(_address(action), params))

    async def async_read_properties(
        self, names: Sequence[Property]
    ) -> dict[str, PropertyValue]:
        """Read the current value of the mapped properties among ``names``."""
        values = await self._run(
            self._client.get_properties(
                {
                    name: self._properties[name]
                    for name in names
                    if name in self._properties
                }
            )
        )
        return self._unmask(values)

    async def async_clean_zones(
        self, zones: Sequence[CleaningZone], repeats: int | None = None
    ) -> None:
        """
        Start cleaning rectangular zones, optionally setting the repeat count.

        The device acknowledges any ``start-zone-sweep`` payload with ``code: 0``
        but only moves for the block list the Mi Home plugin sends; repeats are
        not part of that payload, so they go to the clean-times property first.
        """
        action = self._spec.actions.start_zone_sweep
        if action is None:
            msg = "Failed to clean zones: this model has no zone-sweep action"
            raise XiaomiVacuumApiClientError(msg)
        if repeats is not None:
            await self.async_set_property(Property.CLEAN_TIMES, value=repeats)
        blocks = json.dumps([zone.to_block() for zone in zones], separators=(",", ":"))
        payload: list[JsonValue] = [{"piid": action["in_piid"], "value": blocks}]
        LOGGER.debug("Calling start-zone-sweep with payload: %s", payload)
        await self._run_action(self._client.call_action(_address(action), payload))

    async def async_get_custom_cleanings(self) -> list[CustomCleaning]:
        """Read the custom cleanings saved in the Mi Home app."""
        address = self._properties.get(Property.USER_DEFINE_SWEEP_CONFIG)
        if address is None:
            msg = "Failed to read custom cleanings: this model has no custom cleanings"
            raise XiaomiVacuumApiClientError(msg)
        values = await self._run(self._client.get_properties({"config": address}))
        return CustomCleaning.list_from_config(values.get("config"))

    async def async_start_custom_cleaning(self, cleaning: CustomCleaning) -> None:
        """Start a custom cleaning saved in the Mi Home app."""
        action = self._spec.actions.start_user_define_sweep
        if action is None:
            msg = "Failed to start custom cleaning: this model has no custom cleanings"
            raise XiaomiVacuumApiClientError(msg)
        payload: list[JsonValue] = [
            {"piid": action["in_piid"], "value": cleaning.identifier}
        ]
        LOGGER.debug("Calling start-user-define-sweep with payload: %s", payload)
        await self._run_action(self._client.call_action(_address(action), payload))

    async def async_call_action_reliably(
        self, action: MiotActionAddress, params: list[str]
    ) -> None:
        """
        Invoke a MIoT action, preferring the cloud when a session is available.

        The cloud path (reliable TCP) is used for actions that local UDP
        mishandles on flaky Wi-Fi — multi-step flows like the S20+ room-clean,
        where a single ``-9999`` on the first step would otherwise leave the
        second step running uselessly. When no cloud session is configured we
        fall back to the local path (with its ack-timeout tolerance).
        """
        siid, aiid = action["siid"], action["aiid"]
        if self._cloud is not None:
            try:
                result = await self._cloud.async_call_action(siid, aiid, params)
            except (XiaomiCloudAuthError, XiaomiCloudConnectionError) as exc:
                # Neither an unreachable cloud nor a rejected session may fail
                # the command — the device may still be reachable over the LAN,
                # so fall back to the local transport just like the
                # session-absent case. An expired session is re-prompted at the
                # next entry setup; here it must not break room cleaning.
                LOGGER.warning(
                    "Cloud transport failed for action %s/%s; using local: %s",
                    siid,
                    aiid,
                    exc,
                )
                result = None
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
                    "Cloud transport unavailable for action %s/%s; using local",
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
        await self._run_action(
            self._client.call_action(
                ActionAddress(siid=siid, aiid=aiid), cast("list[JsonValue]", params)
            )
        )


def _mask_shift(mask: int) -> int:
    """Bit position of the lowest set bit of ``mask``."""
    return (mask & -mask).bit_length() - 1


def _address(action: MiotActionAddress) -> ActionAddress:
    """Convert a spec action mapping entry to the SDK's address type."""
    return ActionAddress(siid=action["siid"], aiid=action["aiid"])


def _group_property_requests(
    properties: dict[str, PropertyAddress],
) -> list[dict[str, PropertyAddress]]:
    """Group the properties so each standalone one is read in its own request."""
    shared: dict[str, PropertyAddress] = {}
    standalone: list[dict[str, PropertyAddress]] = []
    for name, address in properties.items():
        if name in _STANDALONE_PROPERTIES:
            standalone.append({name: address})
        else:
            shared[name] = address
    return [shared, *standalone]
