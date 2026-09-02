"""Configuration flow for KilnAid."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import KilnAidApi, KilnAidAuthenticationError, KilnAidConnectionError
from .const import CONF_EMAIL, DOMAIN


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_EMAIL, default=defaults.get(CONF_EMAIL, "")): TextSelector(
                TextSelectorConfig(type=TextSelectorType.EMAIL)
            ),
            vol.Required(CONF_PASSWORD): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
        }
    )


class KilnAidConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the KilnAid configuration flow."""

    VERSION = 1

    async def _validate(self, data: dict[str, Any]) -> str:
        email = str(data[CONF_EMAIL]).strip().lower()
        api = KilnAidApi(
            async_get_clientsession(self.hass), email, data[CONF_PASSWORD]
        )
        await api.async_login()
        return email

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                email = await self._validate(user_input)
            except KilnAidAuthenticationError:
                errors["base"] = "invalid_auth"
            except KilnAidConnectionError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(email)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=email,
                    data={
                        CONF_EMAIL: email,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=_schema(user_input), errors=errors
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        email = entry.data[CONF_EMAIL]
        if user_input is not None:
            data = {CONF_EMAIL: email, CONF_PASSWORD: user_input[CONF_PASSWORD]}
            try:
                await self._validate(data)
            except KilnAidAuthenticationError:
                errors["base"] = "invalid_auth"
            except KilnAidConnectionError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(email)
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=data,
                    reload_even_if_entry_is_unchanged=False,
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    )
                }
            ),
            errors=errors,
        )

