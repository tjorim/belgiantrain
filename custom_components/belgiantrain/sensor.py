"""Get ride details and liveboard details for NMBS (Belgian railway)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    CONF_NAME,
    CONF_SHOW_ON_MAP,
    UnitOfTime,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    CONF_EXCLUDE_VIAS,
    CONF_STATION_FROM,
    CONF_STATION_TO,
    DOMAIN,
    find_station,
)
from .coordinator import BelgianTrainDataUpdateCoordinator

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    from pyrail.models import ConnectionDetails, LiveboardDeparture, StationDetails

_LOGGER = logging.getLogger(__name__)

DEFAULT_ICON = "mdi:train"
DEFAULT_ICON_ALERT = "mdi:alert-octagon"


def get_time_until(departure_time: datetime | None = None) -> int:
    """Calculate the time between now and a train's departure time."""
    if departure_time is None:
        return 0

    delta = dt_util.as_utc(departure_time) - dt_util.utcnow()
    return round(delta.total_seconds() / 60)


def get_delay_in_minutes(delay: int = 0) -> int:
    """Get the delay in minutes from a delay in seconds."""
    return round(int(delay) / 60)


def get_ride_duration(
    departure_time: datetime, arrival_time: datetime, delay: int = 0
) -> int:
    """Calculate the total travel time in minutes."""
    duration = arrival_time - departure_time
    duration_time = round(duration.total_seconds() / 60)
    return duration_time + get_delay_in_minutes(delay)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up NMBS sensor entities based on a config entry."""
    name = config_entry.data.get(CONF_NAME, None)
    show_on_map = config_entry.data.get(CONF_SHOW_ON_MAP, False)
    excl_vias = config_entry.data.get(CONF_EXCLUDE_VIAS, False)

    station_from = find_station(hass, config_entry.data[CONF_STATION_FROM])
    station_to = find_station(hass, config_entry.data[CONF_STATION_TO])

    if station_from is None or station_to is None:
        _LOGGER.error(
            "Could not find station(s): from='%s', to='%s'. Aborting setup.",
            config_entry.data.get(CONF_STATION_FROM),
            config_entry.data.get(CONF_STATION_TO),
        )
        return

    # Get coordinator from hass.data
    coordinator: BelgianTrainDataUpdateCoordinator = hass.data[DOMAIN]["coordinators"][
        config_entry.entry_id
    ]

    # setup the connection from station to station
    # setup a disabled liveboard for both from and to station
    async_add_entities(
        [
            NMBSSensor(
                coordinator, name, show_on_map, station_from, station_to, excl_vias
            ),
            NMBSLiveBoard(
                coordinator, station_from, station_from, station_to, excl_vias
            ),
            NMBSLiveBoard(coordinator, station_to, station_from, station_to, excl_vias),
        ]
    )


class NMBSLiveBoard(CoordinatorEntity[BelgianTrainDataUpdateCoordinator], SensorEntity):
    """Get the next train from a station's liveboard."""

    _attr_attribution = "https://api.irail.be/"

    def __init__(
        self,
        coordinator: BelgianTrainDataUpdateCoordinator,
        live_station: StationDetails,
        station_from: StationDetails,
        station_to: StationDetails,
        excl_vias: bool,  # noqa: FBT001
    ) -> None:
        """Initialize the sensor for getting liveboard data."""
        super().__init__(coordinator)
        self._station = live_station
        self._station_from = station_from
        self._station_to = station_to

        self._excl_vias = excl_vias
        self._attrs: LiveboardDeparture | None = None

        self._state: str | None = None

        self.entity_registry_enabled_default = False

    @property
    def name(self) -> str:
        """Return the sensor default name."""
        return f"Trains in {self._station.standard_name}"

    @property
    def unique_id(self) -> str:
        """Return the unique ID."""
        unique_id = f"{self._station.id}_{self._station_from.id}_{self._station_to.id}"
        vias = "_excl_vias" if self._excl_vias else ""
        return f"nmbs_live_{unique_id}{vias}"

    @property
    def icon(self) -> str:
        """Return the default icon or an alert icon if delays."""
        if self._attrs:
            delay = getattr(self._attrs, "delay", 0)
            if delay and int(delay) > 0:
                return DEFAULT_ICON_ALERT

        return DEFAULT_ICON

    @property
    def native_value(self) -> str | None:
        """Return sensor state."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the sensor attributes if data is available."""
        if self._state is None or not self._attrs:
            return None

        delay = get_delay_in_minutes(self._attrs.delay)
        departure = get_time_until(self._attrs.time)

        attrs = {
            "departure": f"In {departure} minutes",
            "departure_minutes": departure,
            "extra_train": self._attrs.is_extra,
            "vehicle_id": self._attrs.vehicle,
            "monitored_station": self._station.standard_name,
        }

        if delay > 0:
            attrs["delay"] = f"{delay} minutes"
            attrs["delay_minutes"] = delay

        return attrs

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.data is None:
            _LOGGER.warning("Coordinator data not available")
            return

        # Determine which liveboard to use based on station
        if self._station.id == self.coordinator.station_from.id:
            liveboard = self.coordinator.data.get("liveboard_from")
        else:
            liveboard = self.coordinator.data.get("liveboard_to")

        if liveboard is None:
            _LOGGER.warning("Liveboard data not available in coordinator")
            return

        if not (departures := liveboard.departures):
            _LOGGER.warning("API returned invalid departures: %r", liveboard)
            self._state = None
            self._attrs = None
            return

        _LOGGER.debug("Processing departures from coordinator: %r", departures)
        next_departure = departures[0]

        self._attrs = next_departure
        self._state = f"Track {next_departure.platform} - {next_departure.station}"


class NMBSSensor(CoordinatorEntity[BelgianTrainDataUpdateCoordinator], SensorEntity):
    """Get the total travel time for a given connection."""

    _attr_attribution = "https://api.irail.be/"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(  # noqa: PLR0913
        self,
        coordinator: BelgianTrainDataUpdateCoordinator,
        name: str,
        show_on_map: bool,  # noqa: FBT001
        station_from: StationDetails,
        station_to: StationDetails,
        excl_vias: bool,  # noqa: FBT001
    ) -> None:
        """Initialize the NMBS connection sensor."""
        super().__init__(coordinator)
        self._name = name
        self._show_on_map = show_on_map
        self._station_from = station_from
        self._station_to = station_to
        self._excl_vias = excl_vias

        self._attrs: ConnectionDetails | None = None
        self._state = None

    @property
    def unique_id(self) -> str:
        """Return the unique ID."""
        unique_id = f"{self._station_from.id}_{self._station_to.id}"

        vias = "_excl_vias" if self._excl_vias else ""
        return f"nmbs_connection_{unique_id}{vias}"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        if self._name is None:
            return (
                f"Train from {self._station_from.standard_name} "
                f"to {self._station_to.standard_name}"
            )
        return self._name

    @property
    def icon(self) -> str:
        """Return the sensor default icon or an alert icon if any delay."""
        if self._attrs:
            delay = get_delay_in_minutes(self._attrs.departure.delay)
            if delay > 0:
                return "mdi:alert-octagon"

        return "mdi:train"

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return sensor attributes if data is available."""
        if self._state is None or not self._attrs:
            return None

        delay = get_delay_in_minutes(self._attrs.departure.delay)
        departure = get_time_until(self._attrs.departure.time)

        attrs = {
            "destination": self._attrs.departure.station,
            "direction": self._attrs.departure.direction.name,
            "platform_arriving": self._attrs.arrival.platform,
            "platform_departing": self._attrs.departure.platform,
            "vehicle_id": self._attrs.departure.vehicle,
        }

        attrs["canceled"] = self._attrs.departure.canceled
        if attrs["canceled"]:
            attrs["departure"] = None
            attrs["departure_minutes"] = None
        else:
            attrs["departure"] = f"In {departure} minutes"
            attrs["departure_minutes"] = departure

        if self._show_on_map and self.station_coordinates:
            attrs[ATTR_LATITUDE] = self.station_coordinates[0]
            attrs[ATTR_LONGITUDE] = self.station_coordinates[1]

        if self.is_via_connection and not self._excl_vias:
            via = self._attrs.vias[0]

            attrs["via"] = via.station
            attrs["via_arrival_platform"] = via.arrival.platform
            attrs["via_transfer_platform"] = via.departure.platform
            attrs["via_transfer_time"] = get_delay_in_minutes(
                via.timebetween
            ) + get_delay_in_minutes(via.departure.delay)

        attrs["delay"] = f"{delay} minutes"
        attrs["delay_minutes"] = delay

        return attrs

    @property
    def native_value(self) -> int | None:
        """Return the state of the device."""
        return self._state

    @property
    def station_coordinates(self) -> list[float]:
        """Get the lat, long coordinates for station."""
        if self._state is None or not self._attrs:
            return []

        latitude = float(self._attrs.departure.station_info.latitude)
        longitude = float(self._attrs.departure.station_info.longitude)
        return [latitude, longitude]

    @property
    def is_via_connection(self) -> bool:
        """Return whether the connection goes through another station."""
        if not self._attrs:
            return False

        return self._attrs.vias is not None and len(self._attrs.vias) > 0

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.data is None:
            _LOGGER.warning("Coordinator data not available")
            return

        connections = self.coordinator.data.get("connections")

        if connections is None:
            _LOGGER.warning("Connection data not available in coordinator")
            return

        if not (connection := connections.connections):
            _LOGGER.warning("API returned invalid connection: %r", connections)
            self._state = None
            self._attrs = None
            return

        _LOGGER.debug("Processing connection from coordinator: %r", connection)

        # Ensure we have at least one connection
        if len(connection) == 0:
            _LOGGER.warning("No connections available")
            self._state = None
            self._attrs = None
            return

        # Check if first train has already left and we have a second option
        if connection[0].departure.left and len(connection) > 1:
            next_connection = connection[1]
        else:
            next_connection = connection[0]

        self._attrs = next_connection

        if self._excl_vias and self.is_via_connection:
            _LOGGER.debug(
                "Skipping update of NMBSSensor because this connection is a via"
            )
            return

        duration = get_ride_duration(
            next_connection.departure.time,
            next_connection.arrival.time,
            next_connection.departure.delay,
        )

        self._state = duration
