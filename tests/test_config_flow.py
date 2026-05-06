from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.xiaomi_vacuum.const import DOMAIN


async def _start(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_step_user_jumps_straight_to_qr_progress(
    hass, enable_custom_integrations
):
    """Add Hub → no form → QR progress dialog with the PNG embedded."""
    cloud = MagicMock()
    cloud.async_qr_start = AsyncMock(return_value=(b"PNG", "https://lp", 60))

    pending = asyncio.Future()

    async def hang(*_a, **_kw):
        return await pending

    cloud.async_qr_login = hang

    with patch(
        "custom_components.xiaomi_vacuum.config_flow.XiaomiCloud", return_value=cloud
    ):
        try:
            result = await _start(hass)
            assert result["type"] == FlowResultType.SHOW_PROGRESS
            assert result["step_id"] == "qr"
            assert result["progress_action"] == "waiting_for_scan"
            assert (
                "data:image/png;base64,"
                in result["description_placeholders"]["qr_image"]
            )
        finally:
            pending.cancel()
            await asyncio.sleep(0)
