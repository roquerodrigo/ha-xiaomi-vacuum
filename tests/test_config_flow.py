from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.xiaomi_vacuum.api import (
    XiaomiVacuumApiClientCommunicationError,
    XiaomiVacuumApiClientError,
)
from custom_components.xiaomi_vacuum.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_TOKEN,
    DOMAIN,
)


@pytest.fixture
def patch_client_factory():
    """Patch the client class used inside config_flow.py."""
    target = "custom_components.xiaomi_vacuum.config_flow.XiaomiVacuumApiClient"
    with patch(target) as cls:
        yield cls


def _info_mock(model="xiaomi.vacuum.d109gl", mac="AA:BB:CC:DD:EE:FF"):
    info = MagicMock()
    info.model = model
    info.mac_address = mac
    return info


async def _start(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_step_user_shows_form(hass, enable_custom_integrations):
    result = await _start(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_step_user_creates_entry_with_user_name(
    hass, enable_custom_integrations, patch_client_factory
):
    patch_client_factory.return_value.async_get_info = AsyncMock(
        return_value=_info_mock()
    )
    flow = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"],
        user_input={CONF_HOST: "1.2.3.4", CONF_TOKEN: "t" * 32, CONF_NAME: "Sala"},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Sala"
    assert result["data"][CONF_NAME] == "Sala"


async def test_step_user_falls_back_to_model_name(
    hass, enable_custom_integrations, patch_client_factory
):
    patch_client_factory.return_value.async_get_info = AsyncMock(
        return_value=_info_mock()
    )
    flow = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"],
        user_input={CONF_HOST: "1.2.3.4", CONF_TOKEN: "t" * 32, CONF_NAME: ""},
    )
    assert result["title"] == "xiaomi.vacuum.d109gl"


async def test_step_user_uses_mac_as_unique_id(
    hass, enable_custom_integrations, patch_client_factory
):
    patch_client_factory.return_value.async_get_info = AsyncMock(
        return_value=_info_mock(mac="11:22:33:44:55:66")
    )
    flow = await _start(hass)
    await hass.config_entries.flow.async_configure(
        flow["flow_id"],
        user_input={CONF_HOST: "1.2.3.4", CONF_TOKEN: "t" * 32},
    )
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.unique_id == "11:22:33:44:55:66"


async def test_step_user_duplicate_aborts(
    hass, enable_custom_integrations, patch_client_factory
):
    patch_client_factory.return_value.async_get_info = AsyncMock(
        return_value=_info_mock()
    )
    flow1 = await _start(hass)
    await hass.config_entries.flow.async_configure(
        flow1["flow_id"],
        user_input={CONF_HOST: "1.2.3.4", CONF_TOKEN: "t" * 32},
    )
    flow2 = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        flow2["flow_id"],
        user_input={CONF_HOST: "1.2.3.4", CONF_TOKEN: "t" * 32},
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_step_user_communication_error(
    hass, enable_custom_integrations, patch_client_factory
):
    patch_client_factory.return_value.async_get_info = AsyncMock(
        side_effect=XiaomiVacuumApiClientCommunicationError("offline")
    )
    flow = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"],
        user_input={CONF_HOST: "1.2.3.4", CONF_TOKEN: "t" * 32},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "connection"


async def test_step_user_unknown_error(
    hass, enable_custom_integrations, patch_client_factory
):
    patch_client_factory.return_value.async_get_info = AsyncMock(
        side_effect=XiaomiVacuumApiClientError("boom")
    )
    flow = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"],
        user_input={CONF_HOST: "1.2.3.4", CONF_TOKEN: "t" * 32},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "unknown"
