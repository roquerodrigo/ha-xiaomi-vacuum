"""Custom cleaning saved in the Mi Home app."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..const import LOGGER  # noqa: TID252

if TYPE_CHECKING:
    from xiaomi_vacuum_sdk import PropertyValue

    from ..data import JsonValue  # noqa: TID252


@dataclass(frozen=True)
class CustomCleaning:
    """A named cleaning preset the robot stores and runs by its identifier."""

    identifier: int
    name: str

    @classmethod
    def list_from_config(cls, raw: PropertyValue) -> list[CustomCleaning]:
        """Parse the ``user-define-sweep-cfg`` payload, skipping malformed entries."""
        if not isinstance(raw, str) or not raw:
            return []
        try:
            config: JsonValue = json.loads(raw)
        except ValueError:
            LOGGER.warning("Could not JSON-parse user-define-sweep-cfg: %r", raw)
            return []
        labels = config.get("user_labels") if isinstance(config, dict) else None
        if not isinstance(labels, list):
            return []
        cleanings: list[CustomCleaning] = []
        for label in labels:
            if not isinstance(label, dict):
                continue
            identifier = label.get("id")
            name = label.get("name")
            if isinstance(identifier, int) and isinstance(name, str):
                cleanings.append(cls(identifier=identifier, name=name))
        return cleanings

    def matches(self, name: str) -> bool:
        """Whether ``name`` refers to this cleaning, ignoring case and padding."""
        return self.name.strip().casefold() == name.strip().casefold()
