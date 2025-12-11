"""The SNCB/NMBS integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pyrail import iRail

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]


CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up the NMBS component."""
    api_client = iRail(session=async_get_clientsession(hass))

    hass.data.setdefault(DOMAIN, {})
    station_response = await api_client.get_stations()
    if station_response is None:
        _LOGGER.error(
            "Failed to fetch stations from the iRail API. "
            "The iRail API may be unavailable. Aborting integration setup."
        )
        return False
    hass.data[DOMAIN] = station_response.stations

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SNCB/NMBS from a config entry."""
    # Ensure station data exists and is a list before setting up platforms
    stations = hass.data.get(DOMAIN)
    if not isinstance(stations, list) or not stations:
        _LOGGER.error("Station data is missing or invalid; cannot set up platforms.")
        return False

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
