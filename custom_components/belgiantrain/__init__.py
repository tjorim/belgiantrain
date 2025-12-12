"""The SNCB/NMBS integration."""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pyrail import iRail

from .const import CONF_STATION_FROM, CONF_STATION_TO, DOMAIN, find_station
from .coordinator import BelgianTrainDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]


CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def _async_get_disturbances_handler(
    hass: HomeAssistant, call: ServiceCall
) -> ServiceResponse:
    """Handle the get_disturbances service call."""
    line_break_character = call.data.get("line_break_character")

    api_client = iRail(session=async_get_clientsession(hass))
    disturbances = await api_client.get_disturbances(
        line_break_character=line_break_character
    )

    if disturbances is None:
        return {"disturbances": []}

    # Convert disturbances to dict format for response
    disturbance_list = [
        {
            "id": disturbance.id,
            "title": disturbance.title,
            "description": disturbance.description,
            "type": disturbance.type,
            "timestamp": (
                disturbance.timestamp.isoformat() if disturbance.timestamp else None
            ),
        }
        for disturbance in disturbances.disturbances
    ]

    return {"disturbances": disturbance_list}


async def _async_get_vehicle_handler(
    hass: HomeAssistant, call: ServiceCall
) -> ServiceResponse:
    """Handle the get_vehicle service call."""
    vehicle_id = call.data["vehicle_id"]
    date = call.data.get("date")
    alerts = call.data.get("alerts", False)

    api_client = iRail(session=async_get_clientsession(hass))
    vehicle = await api_client.get_vehicle(id=vehicle_id, date=date, alerts=alerts)

    if vehicle is None:
        return {"vehicle_id": vehicle_id, "error": "Vehicle not found or API error"}

    # Convert vehicle info to dict format for response
    stops = [
        {
            "station": stop.station,
            "platform": stop.platform,
            "time": stop.time.isoformat() if stop.time else None,
            "delay": stop.delay,
            "canceled": stop.canceled,
        }
        for stop in vehicle.stops
    ]

    return {
        "vehicle_id": vehicle.vehicle,
        "name": getattr(vehicle, "name", None),
        "stops": stops,
    }


async def _async_get_composition_handler(
    hass: HomeAssistant, call: ServiceCall
) -> ServiceResponse:
    """Handle the get_composition service call."""
    train_id = call.data["train_id"]

    api_client = iRail(session=async_get_clientsession(hass))
    composition = await api_client.get_composition(id=train_id)

    if composition is None:
        return {
            "train_id": train_id,
            "error": "Train composition not found or API error",
        }

    # Convert composition info to dict format for response
    composition_data = {
        "train_id": train_id,
        "segments": [],
    }

    if hasattr(composition, "composition") and composition.composition:
        # Build segments list from composition data
        segments = []
        if hasattr(composition.composition, "segments"):
            for segment in composition.composition.segments:
                segment_data = {
                    "origin": getattr(segment, "origin", None),
                    "destination": getattr(segment, "destination", None),
                }

                # Add composition units if available
                if hasattr(segment, "composition") and segment.composition:
                    units = []
                    if hasattr(segment.composition, "units"):
                        for unit in segment.composition.units:
                            unit_data = {
                                "material_type": getattr(unit, "material_type", None),
                                "has_toilet": getattr(unit, "has_toilet", False),
                                "has_bike_section": getattr(
                                    unit, "has_bike_section", False
                                ),
                                "has_prm_section": getattr(
                                    unit, "has_prmSection", False
                                ),
                            }
                            units.append(unit_data)
                    segment_data["units"] = units

                segments.append(segment_data)

        composition_data["segments"] = segments

    return composition_data


async def _async_get_stations_handler(
    hass: HomeAssistant, call: ServiceCall
) -> ServiceResponse:
    """Handle the get_stations service call."""
    name_filter = call.data.get("name_filter", "").lower()

    # Use cached station data from hass.data
    stations = hass.data[DOMAIN].get("stations", [])

    # Filter stations if name_filter provided
    if name_filter:
        filtered_stations = []
        for station in stations:
            name_lower = station.name.lower()
            standard_name_lower = station.standard_name.lower()
            if name_filter in name_lower or name_filter in standard_name_lower:
                filtered_stations.append(
                    {
                        "id": station.id,
                        "name": station.name,
                        "standard_name": station.standard_name,
                        "latitude": getattr(station, "latitude", None),
                        "longitude": getattr(station, "longitude", None),
                    }
                )
    else:
        filtered_stations = [
            {
                "id": station.id,
                "name": station.name,
                "standard_name": station.standard_name,
                "latitude": getattr(station, "latitude", None),
                "longitude": getattr(station, "longitude", None),
            }
            for station in stations
        ]

    return {"stations": filtered_stations, "count": len(filtered_stations)}


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
    # Store stations in a dict to allow storing coordinators later
    hass.data[DOMAIN] = {"stations": station_response.stations, "coordinators": {}}

    # Register services with partial to bind hass
    hass.services.async_register(
        DOMAIN,
        "get_disturbances",
        partial(_async_get_disturbances_handler, hass),
        supports_response=True,
    )

    hass.services.async_register(
        DOMAIN,
        "get_vehicle",
        partial(_async_get_vehicle_handler, hass),
        supports_response=True,
    )

    hass.services.async_register(
        DOMAIN,
        "get_composition",
        partial(_async_get_composition_handler, hass),
        supports_response=True,
    )

    hass.services.async_register(
        DOMAIN,
        "get_stations",
        partial(_async_get_stations_handler, hass),
        supports_response=True,
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SNCB/NMBS from a config entry."""
    # Ensure station data exists before setting up platforms
    domain_data = hass.data.get(DOMAIN)
    if not isinstance(domain_data, dict) or "stations" not in domain_data:
        _LOGGER.error("Station data is missing or invalid; cannot set up platforms.")
        return False

    # Get stations from config entry
    station_from = find_station(hass, entry.data[CONF_STATION_FROM])
    station_to = find_station(hass, entry.data[CONF_STATION_TO])

    if station_from is None or station_to is None:
        _LOGGER.error(
            "Could not find station(s): from='%s', to='%s'. Aborting setup.",
            entry.data.get(CONF_STATION_FROM),
            entry.data.get(CONF_STATION_TO),
        )
        return False

    # Create API client and coordinator
    api_client = iRail(session=async_get_clientsession(hass))
    coordinator = BelgianTrainDataUpdateCoordinator(
        hass, api_client, station_from, station_to
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator
    hass.data[DOMAIN]["coordinators"][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Remove coordinator from hass.data
        hass.data[DOMAIN]["coordinators"].pop(entry.entry_id, None)

        # Unregister services if this is the last entry
        if not hass.data[DOMAIN]["coordinators"]:
            hass.services.async_remove(DOMAIN, "get_disturbances")
            hass.services.async_remove(DOMAIN, "get_vehicle")
            hass.services.async_remove(DOMAIN, "get_composition")
            hass.services.async_remove(DOMAIN, "get_stations")

    return unload_ok
