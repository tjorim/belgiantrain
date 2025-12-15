"""Constants for the SNCB/NMBS integration."""

from typing import TYPE_CHECKING, Final

from homeassistant.const import Platform

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pyrail.models import StationDetails

DOMAIN: Final = "belgiantrain"

PLATFORMS: Final = [Platform.SENSOR]

CONF_STATION_FROM = "station_from"
CONF_STATION_TO = "station_to"
CONF_STATION_LIVE = "station_live"
CONF_EXCLUDE_VIAS = "exclude_vias"
CONF_SHOW_ON_MAP = "show_on_map"

# Subentry types
SUBENTRY_TYPE_CONNECTION: Final = "connection"
SUBENTRY_TYPE_LIVEBOARD: Final = "liveboard"

# Config entry unique ID prefixes
CONFIG_ENTRY_PREFIX_CONNECTION: Final = "config_connection_"
CONFIG_ENTRY_PREFIX_LIVEBOARD: Final = "config_liveboard_"


def find_station_by_name(
    hass: "HomeAssistant", station_name: str
) -> "StationDetails | None":
    """Find given station_name in the station list."""
    stations = hass.data.get(DOMAIN, {})
    station_list = stations.get("stations", [])

    return next(
        (s for s in station_list if station_name in (s.standard_name, s.name)),
        None,
    )


def find_station(hass: "HomeAssistant", station_id: str) -> "StationDetails | None":
    """Find station by exact station_id in the station list."""
    stations = hass.data.get(DOMAIN, {})
    station_list = stations.get("stations", [])

    return next(
        (s for s in station_list if s.id == station_id),
        None,
    )
