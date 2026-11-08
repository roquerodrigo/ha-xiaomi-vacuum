"""Tests keeping the translation files consistent with each other and the code."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.xiaomi_vacuum.const import DOMAIN
from custom_components.xiaomi_vacuum.spec import StatusSlug

TRANSLATIONS_DIR = (
    Path(__file__).parent.parent
    / "custom_components"
    / "xiaomi_vacuum"
    / "translations"
)


def _flatten_keys(data, prefix=""):
    keys = set()
    if isinstance(data, dict):
        for key, value in data.items():
            full = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                keys |= _flatten_keys(value, full)
            else:
                keys.add(full)
    return keys


def _translation_files():
    return sorted(TRANSLATIONS_DIR.glob("*.json"))


def _key_sets():
    return {
        f.stem: _flatten_keys(json.loads(f.read_text(encoding="utf-8")))
        for f in _translation_files()
    }


def test_translations_directory_has_at_least_two_locales():
    assert len(_translation_files()) >= 2


def test_en_locale_exists():
    assert (TRANSLATIONS_DIR / "en.json").exists()


@pytest.mark.parametrize("locale", [f.stem for f in _translation_files()])
def test_translation_locale_matches_en_keys(locale):
    sets = _key_sets()
    reference = sets["en"]
    other = sets[locale]
    missing = reference - other
    extra = other - reference
    assert not missing, f"{locale}.json is missing keys: {sorted(missing)}"
    assert not extra, f"{locale}.json has unexpected keys: {sorted(extra)}"


def _authored_entity_keys() -> set[tuple[str, str]]:
    """Return every `(platform, key)` pair `en.json` defines under `entity`."""
    entity_section = json.loads(
        (TRANSLATIONS_DIR / "en.json").read_text(encoding="utf-8"),
    )["entity"]
    return {
        (platform, key) for platform, blocks in entity_section.items() for key in blocks
    }


async def _add_x20_plus(hass, make_miot_instance) -> None:
    """Set up an X20+ next to the X20 Max, adding its Dreame-only entities."""
    from unittest.mock import patch

    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.xiaomi_vacuum.const import CONF_HOST, CONF_NAME, CONF_TOKEN

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.53", CONF_TOKEN: "0" * 32, CONF_NAME: "X20 Plus"},
        unique_id="AA:BB:CC:DD:EE:03",
    )
    entry.add_to_hass(hass)
    with patch("custom_components.xiaomi_vacuum.api.client.MiotClient") as cls:
        cls.return_value = make_miot_instance("xiaomi.vacuum.c102gl")
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


async def test_entity_translation_keys_and_authored_names_agree(
    hass,
    setup_integration_with_cloud,
    make_miot_instance,
):
    """
    Every translation key an entity asks for is authored, and vice versa.

    Read from the entity registry rather than the classes: Home Assistant
    rewrites `_attr_translation_key` into a property, so inspecting the class
    attribute finds a descriptor and quietly checks nothing. Comparing the
    locales against each other cannot catch this either — a key missing from
    both sides matches, and the entity falls back to its device-class name
    while the authored one never shows. The cloud-backed X20 Max fixture
    (the map image entity included) plus an X20+ for the Dreame-only extras
    create the full entity roster, so their registry covers every authored key.
    """
    from homeassistant.helpers import entity_registry as er

    await _add_x20_plus(hass, make_miot_instance)

    registry = er.async_get(hass)
    requested = {
        (entry.domain, entry.translation_key)
        for entry in registry.entities.values()
        if entry.platform == DOMAIN and entry.translation_key is not None
    }
    assert requested, "the integration registered no translated entity"
    authored = _authored_entity_keys()
    assert not requested - authored, (
        f"entities ask for keys en.json does not define: {sorted(requested - authored)}"
    )
    assert not authored - requested, (
        f"en.json defines keys no entity asks for: {sorted(authored - requested)}"
    )


def test_every_status_slug_is_translated():
    english = json.loads((TRANSLATIONS_DIR / "en.json").read_text(encoding="utf-8"))
    states = english["entity"]["sensor"]["status"]["state"]
    assert set(StatusSlug) <= set(states)


def test_no_empty_translation_values():
    for path in _translation_files():
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in _flatten_keys(data):
            value = data
            for part in key.split("."):
                value = value[part]
            assert value, f"{path.name} has empty value for {key}"
