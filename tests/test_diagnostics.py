"""Tests for the config entry diagnostics."""

from __future__ import annotations

from homeassistant.components.diagnostics import REDACTED

from custom_components.xiaomi_vacuum.diagnostics import (
    TO_REDACT,
    async_get_config_entry_diagnostics,
)


async def test_diagnostics_redacts_cloud_credentials(
    hass, setup_integration_with_cloud
):
    entry = setup_integration_with_cloud
    payload = await async_get_config_entry_diagnostics(hass, entry)
    data = payload["entry"]["data"]
    for secret_key in TO_REDACT:
        assert data[secret_key] == REDACTED
    assert data["host"] == "192.168.1.50"
    assert payload["entry"]["title"] == entry.title
    assert payload["entry"]["domain"] == "xiaomi_vacuum"


async def test_diagnostics_reports_device_and_coordinator_state(
    hass, setup_integration_with_cloud
):
    payload = await async_get_config_entry_diagnostics(
        hass, setup_integration_with_cloud
    )
    assert payload["device"]["model"] == "xiaomi.vacuum.d109gl"
    assert payload["device"]["supported"] is True
    assert payload["device"]["firmware_version"] == "1.0.0"
    assert payload["coordinator_state"]["status"] == 2
    assert payload["coordinator_last_update_success"] is True
    assert payload["has_cloud_session"] is True


async def test_diagnostics_without_cloud_session(hass, setup_integration):
    payload = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert payload["has_cloud_session"] is False
    assert "cloud_ssecurity" not in payload["entry"]["data"]
    assert payload["entry"]["data"]["token"] == REDACTED
