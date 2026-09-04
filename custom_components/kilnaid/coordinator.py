"""KilnAid update coordinator."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    KilnAidApi,
    KilnAidAuthenticationError,
    KilnAidConnectionError,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .models import KilnData
from .history import KilnHistory

_LOGGER = logging.getLogger(__name__)


class KilnAidCoordinator(DataUpdateCoordinator[dict[str, KilnData]]):
    """Coordinate a single poll shared by every KilnAid entity."""

    config_entry: ConfigEntry

    def __init__(self, hass, entry: ConfigEntry, api: KilnAidApi) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
            config_entry=entry,
        )
        self.api = api
        self.history = KilnHistory(hass, entry)

    async def _async_update_data(self) -> dict[str, KilnData]:
        try:
            kilns = await self.api.async_get_kilns()
        except KilnAidAuthenticationError as err:
            raise ConfigEntryAuthFailed from err
        except KilnAidConnectionError as err:
            raise UpdateFailed(str(err)) from err
        await self.history.async_observe(kilns)
        return {kiln.serial: kiln for kiln in kilns}
