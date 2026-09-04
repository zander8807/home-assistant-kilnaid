"""KilnAid integration for Home Assistant."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import KilnAidApi
from .const import CONF_EMAIL, CONF_PASSWORD, PLATFORMS
from .coordinator import KilnAidCoordinator
from .history import async_setup_history


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Serve the optional companion card and authenticated history API."""
    await async_setup_history(hass)
    return True


@dataclass(slots=True)
class KilnAidRuntimeData:
    """Runtime data stored on the config entry."""

    api: KilnAidApi
    coordinator: KilnAidCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up KilnAid from a config entry."""
    api = KilnAidApi(
        async_get_clientsession(hass),
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD],
    )
    coordinator = KilnAidCoordinator(hass, entry, api)
    await coordinator.history.async_load()
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = KilnAidRuntimeData(api=api, coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a KilnAid config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

