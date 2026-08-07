from __future__ import annotations

from homeassistant.helpers import issue_registry as ir

from custom_components.xiaomi_vacuum.const import CONF_HOST, DOMAIN
from custom_components.xiaomi_vacuum.repairs import (
    async_clear_cannot_connect,
    async_clear_unsupported_model,
    async_raise_cannot_connect,
    async_raise_unsupported_model,
)


def _fake_entry():
    return type(
        "E",
        (),
        {
            "entry_id": "repair-entry",
            "title": "Vacuum",
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
        "name": "Vacuum",
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


async def test_raise_unsupported_model_creates_issue_with_model(hass):
    entry = _fake_entry()
    async_raise_unsupported_model(hass, entry, "xiaomi.vacuum.zzzzz")
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "unsupported_model_repair-entry")
    assert issue is not None
    assert issue.severity == ir.IssueSeverity.WARNING
    assert issue.is_fixable is False
    assert issue.translation_placeholders == {
        "name": "Vacuum",
        "model": "xiaomi.vacuum.zzzzz",
    }


async def test_unsupported_model_raise_then_clear_are_idempotent(hass):
    entry = _fake_entry()
    async_raise_unsupported_model(hass, entry, "xiaomi.vacuum.zzzzz")
    async_raise_unsupported_model(hass, entry, "xiaomi.vacuum.zzzzz")
    registry = ir.async_get(hass)
    assert (
        registry.async_get_issue(DOMAIN, "unsupported_model_repair-entry") is not None
    )

    async_clear_unsupported_model(hass, entry)
    async_clear_unsupported_model(hass, entry)
    assert registry.async_get_issue(DOMAIN, "unsupported_model_repair-entry") is None
