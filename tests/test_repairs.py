from __future__ import annotations

from homeassistant.helpers import issue_registry as ir

from custom_components.xiaomi_vacuum.const import CONF_HOST, DOMAIN
from custom_components.xiaomi_vacuum.repairs import (
    async_clear_cannot_connect,
    async_raise_cannot_connect,
)


def _fake_entry():
    return type(
        "E",
        (),
        {
            "entry_id": "repair-entry",
            "title": "Aspirador",
            "data": {CONF_HOST: "192.168.1.50"},
        },
    )()


async def test_raise_creates_issue_with_placeholders(hass):
    entry = _fake_entry()
    async_raise_cannot_connect(hass, entry)
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "cannot_connect_repair-entry")
    assert issue is not None
    assert issue.severity == ir.IssueSeverity.WARNING
    assert issue.is_fixable is False
    assert issue.translation_placeholders == {
        "name": "Aspirador",
        "host": "192.168.1.50",
    }


async def test_raise_then_clear_are_idempotent(hass):
    entry = _fake_entry()
    async_raise_cannot_connect(hass, entry)
    async_raise_cannot_connect(hass, entry)
    registry = ir.async_get(hass)
    assert registry.async_get_issue(DOMAIN, "cannot_connect_repair-entry") is not None

    async_clear_cannot_connect(hass, entry)
    async_clear_cannot_connect(hass, entry)
    assert registry.async_get_issue(DOMAIN, "cannot_connect_repair-entry") is None
