"""The SNCB/NMBS integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pyrail import iRail

from .const import (
    CONF_EXCLUDE_VIAS,
    CONF_STATION_FROM,
    CONF_STATION_LIVE,
    CONF_STATION_TO,
    DOMAIN,
    SUBENTRY_TYPE_CONNECTION,
    SUBENTRY_TYPE_LIVEBOARD,
    find_station,
)
from .coordinator import (
    BelgianTrainDataUpdateCoordinator,
    LiveboardDataUpdateCoordinator,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]


CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:  # noqa: PLR0915
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
    hass.data[DOMAIN] = {
        "stations": station_response.stations,
        "coordinators": {},
        "api_client": api_client,
    }

    # Define service handlers as nested functions
    async def async_get_disturbances(call: ServiceCall) -> ServiceResponse:
        """Handle the get_disturbances service call."""
        line_break_character = call.data.get("line_break_character")

        try:
            api_client = hass.data[DOMAIN]["api_client"]
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
                        disturbance.timestamp.isoformat()
                        if disturbance.timestamp
                        else None
                    ),
                }
                for disturbance in disturbances.disturbances
            ]

            return {"disturbances": disturbance_list}  # noqa: TRY300
        except Exception as err:
            _LOGGER.exception("Error fetching disturbances")
            return {"disturbances": [], "error": str(err)}

    async def async_get_vehicle(call: ServiceCall) -> ServiceResponse:
        """Handle the get_vehicle service call."""
        vehicle_id = call.data["vehicle_id"]
        date = call.data.get("date")
        alerts = call.data.get("alerts", False)

        try:
            api_client = hass.data[DOMAIN]["api_client"]
            vehicle = await api_client.get_vehicle(
                id=vehicle_id, date=date, alerts=alerts
            )

            if vehicle is None:
                return {
                    "vehicle_id": vehicle_id,
                    "error": "Vehicle not found or API error",
                }

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
        except Exception as err:
            _LOGGER.exception("Error fetching vehicle %s", vehicle_id)
            return {"vehicle_id": vehicle_id, "error": str(err)}

    async def async_get_composition(call: ServiceCall) -> ServiceResponse:
        """Handle the get_composition service call."""
        train_id = call.data["train_id"]

        try:
            api_client = hass.data[DOMAIN]["api_client"]
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
                                        "material_type": getattr(
                                            unit, "material_type", None
                                        ),
                                        "has_toilet": getattr(
                                            unit, "has_toilet", False
                                        ),
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

            return composition_data  # noqa: TRY300
        except Exception as err:
            _LOGGER.exception("Error fetching composition for %s", train_id)
            return {"train_id": train_id, "error": str(err)}

    async def async_get_stations(call: ServiceCall) -> ServiceResponse:
        """Handle the get_stations service call."""
        name_filter = call.data.get("name_filter", "").lower()

        try:
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
        except Exception as err:
            _LOGGER.exception("Error fetching stations")
            return {"stations": [], "count": 0, "error": str(err)}

    # Register services
    hass.services.async_register(
        DOMAIN,
        "get_disturbances",
        async_get_disturbances,
        supports_response=True,
    )

    hass.services.async_register(
        DOMAIN,
        "get_vehicle",
        async_get_vehicle,
        supports_response=True,
    )

    hass.services.async_register(
        DOMAIN,
        "get_composition",
        async_get_composition,
        supports_response=True,
    )

    hass.services.async_register(
        DOMAIN,
        "get_stations",
        async_get_stations,
        supports_response=True,
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:  # noqa: PLR0911, PLR0912, PLR0915
    """Set up SNCB/NMBS from a config entry."""
    # Ensure station data exists before setting up platforms
    domain_data = hass.data.get(DOMAIN)
    if not isinstance(domain_data, dict) or "stations" not in domain_data:
        _LOGGER.error("Station data is missing or invalid; cannot set up platforms.")
        return False

    # Check if this is the main integration entry (no subentry type)
    if entry.subentry_type is None:
        # Check if this is a legacy connection entry (has CONF_STATION_FROM/TO directly)
        # If so, skip this block and let it be handled by legacy support code below
        is_legacy_connection = (
            CONF_STATION_FROM in entry.data and CONF_STATION_TO in entry.data
        )

        if not is_legacy_connection:
            # Main integration entry - check for initial data to create first subentry
            if "first_connection" in entry.data:
                # Create a connection subentry from the initial setup
                connection_data = entry.data["first_connection"]
                if connection_data.get(CONF_STATION_FROM) == connection_data.get(
                    CONF_STATION_TO
                ):
                    _LOGGER.error("Cannot create connection with same station")
                    return False

                # Create connection subentry
                station_from_id = connection_data[CONF_STATION_FROM]
                station_to_id = connection_data[CONF_STATION_TO]
                excl_vias = connection_data.get(CONF_EXCLUDE_VIAS, False)
                vias = "_excl_vias" if excl_vias else ""

                station_from = find_station(hass, station_from_id)
                station_to = find_station(hass, station_to_id)

                if station_from and station_to:
                    await hass.config_entries.async_add_subentry(
                        entry,
                        title=(
                            f"Connection: {station_from.standard_name} → "
                            f"{station_to.standard_name}"
                        ),
                        data=connection_data,
                        unique_id=f"connection_{station_from_id}_{station_to_id}{vias}",
                        subentry_type=SUBENTRY_TYPE_CONNECTION,
                    )

                    # Create liveboard subentries if requested
                    if "liveboards_to_add" in entry.data:
                        # Use set to ensure unique station IDs
                        unique_station_ids = set(entry.data["liveboards_to_add"])
                        for station_id in unique_station_ids:
                            station = find_station(hass, station_id)
                            if station:
                                await hass.config_entries.async_add_subentry(
                                    entry,
                                    title=f"Liveboard - {station.standard_name}",
                                    data={CONF_STATION_LIVE: station_id},
                                    unique_id=f"liveboard_{station_id}",
                                    subentry_type=SUBENTRY_TYPE_LIVEBOARD,
                                )

            elif "first_liveboard" in entry.data:
                # Create a liveboard subentry from the initial setup
                liveboard_data = entry.data["first_liveboard"]
                station_id = liveboard_data[CONF_STATION_LIVE]
                station = find_station(hass, station_id)

                if station:
                    await hass.config_entries.async_add_subentry(
                        entry,
                        title=f"Liveboard - {station.standard_name}",
                        data=liveboard_data,
                        unique_id=f"liveboard_{station_id}",
                        subentry_type=SUBENTRY_TYPE_LIVEBOARD,
                    )

            # Main entry enables subentries
            _LOGGER.info("Main SNCB/NMBS integration entry set up successfully")
            return True

    # Check if this is a subentry for a standalone liveboard
    if entry.subentry_type == SUBENTRY_TYPE_LIVEBOARD:
        # Get station from config entry
        station = find_station(hass, entry.data[CONF_STATION_LIVE])

        if station is None:
            _LOGGER.error(
                "Could not find station: '%s'. Aborting setup.",
                entry.data.get(CONF_STATION_LIVE),
            )
            return False

        # Create API client and coordinator for liveboard
        api_client = iRail(session=async_get_clientsession(hass))
        coordinator = LiveboardDataUpdateCoordinator(hass, api_client, station)

        # Fetch initial data
        await coordinator.async_config_entry_first_refresh()

        # Store coordinator
        hass.data[DOMAIN]["coordinators"][entry.entry_id] = coordinator

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        return True

    # Check if this is a subentry for a connection
    if entry.subentry_type == SUBENTRY_TYPE_CONNECTION:
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

    # Legacy support: entries without subentry_type are connections
    # (for backward compatibility with existing configurations)
    station_from = find_station(hass, entry.data.get(CONF_STATION_FROM, ""))
    station_to = find_station(hass, entry.data.get(CONF_STATION_TO, ""))

    if station_from is None or station_to is None:
        _LOGGER.warning(
            "Legacy connection entry found but stations not valid. "
            "Please reconfigure this entry."
        )
        return False

    # Create API client and coordinator for legacy connection
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

    return unload_ok
