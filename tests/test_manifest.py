from __future__ import annotations

import json
import tomllib
from pathlib import Path


def test_manifest_sdk_pin_matches_dev_group() -> None:
    """The SDK version HA installs is the one the test suite runs against."""
    manifest = json.loads(
        Path("custom_components/xiaomi_vacuum/manifest.json").read_text()
    )
    requirement = next(
        item
        for item in manifest["requirements"]
        if item.startswith("xiaomi-vacuum-sdk")
    )
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    assert requirement in pyproject["dependency-groups"]["dev"]
