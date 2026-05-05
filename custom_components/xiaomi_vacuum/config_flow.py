"""Config flow for Xiaomi Vacuum."""

from __future__ import annotations

import os

import voluptuous as vol
from homeassistant import config_entries

from .api import (
    XiaomiVacuumApiClient,
    XiaomiVacuumApiClientCommunicationError,
    XiaomiVacuumApiClientError,
)
from .const import (
    CONF_HOST,
    CONF_NAME,
    CONF_TOKEN,
    DOMAIN,
    ENV_HOST,
    ENV_NAME,
    ENV_TOKEN,
    LOGGER,
)


class XiaomiVacuumFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Xiaomi Vacuum."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client = XiaomiVacuumApiClient(
                hass=self.hass,
                host=user_input[CONF_HOST],
                token=user_input[CONF_TOKEN],
            )
            try:
                info = await client.async_get_info()
            except XiaomiVacuumApiClientCommunicationError as exception:
                LOGGER.error(exception)
                errors["base"] = "connection"
            except XiaomiVacuumApiClientError as exception:
                LOGGER.exception(exception)
                errors["base"] = "unknown"
            else:
                unique_id = getattr(info, "mac_address", None) or user_input[CONF_HOST]
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                name = (
                    user_input.get(CONF_NAME)
                    or getattr(info, "model", None)
                    or "Xiaomi Vacuum"
                )
                user_input[CONF_NAME] = name
                return self.async_create_entry(title=name, data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    default=(user_input or {}).get(CONF_HOST)
                    or os.environ.get(ENV_HOST, ""),
                ): str,
                vol.Required(
                    CONF_TOKEN,
                    default=(user_input or {}).get(CONF_TOKEN)
                    or os.environ.get(ENV_TOKEN, ""),
                ): str,
                vol.Optional(
                    CONF_NAME,
                    default=(user_input or {}).get(CONF_NAME)
                    or os.environ.get(ENV_NAME, ""),
                ): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
