"""Test the SNCB/NMBS sensor platform."""

# ruff: noqa: ANN001, ANN201, ANN202, ARG001, FBT003, PLC0415, PLR2004

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.belgiantrain.const import (
    CONF_EXCLUDE_VIAS,
    CONF_SHOW_ON_MAP,
    CONF_STATION_FROM,
    CONF_STATION_TO,
    DOMAIN,
)
from custom_components.belgiantrain.sensor import (
    BelgianTrainConnectionSensor,
    get_delay_in_minutes,
    get_ride_duration,
    get_time_until,
)


@pytest.fixture
def mock_stations():
    """Create mock station data."""
    mock_station_1 = MagicMock()
    mock_station_1.id = "BE.NMBS.008812005"
    mock_station_1.standard_name = "Brussels-Central"
    mock_station_1.name = "Brussels-Central"

    mock_station_2 = MagicMock()
    mock_station_2.id = "BE.NMBS.008892007"
    mock_station_2.standard_name = "Ghent-Sint-Pieters"
    mock_station_2.name = "Ghent-Sint-Pieters"

    return [mock_station_1, mock_station_2]


@pytest.fixture
def mock_config_entry(mock_stations):
    """Create a mock config entry."""
    entry = MagicMock()
    entry.data = {
        CONF_STATION_FROM: "BE.NMBS.008812005",
        CONF_STATION_TO: "BE.NMBS.008892007",
        CONF_EXCLUDE_VIAS: False,
        CONF_SHOW_ON_MAP: True,
    }
    return entry


async def test_sensor_setup(hass: HomeAssistant, mock_stations, mock_config_entry):
    """Test sensor platform setup."""
    hass.data[DOMAIN] = mock_stations

    # Mock the iRail API
    with patch("custom_components.belgiantrain.sensor.iRail") as mock_irail:
        mock_api = AsyncMock()
        mock_irail.return_value = mock_api

        # Import and call async_setup_entry
        from custom_components.belgiantrain.sensor import async_setup_entry

        entities = []

        def mock_add_entities(entity_list):
            entities.extend(entity_list)

        await async_setup_entry(hass, mock_config_entry, mock_add_entities)

        # Should create 1 connection sensor (no legacy liveboards for HA 2025.2+)
        assert len(entities) == 1
        assert isinstance(entities[0], BelgianTrainConnectionSensor)


async def test_sensor_setup_missing_station(hass: HomeAssistant, mock_config_entry):
    """Test sensor setup with missing station data."""
    # Don't populate hass.data[DOMAIN] to simulate missing stations
    hass.data[DOMAIN] = []

    with patch("custom_components.belgiantrain.sensor.iRail"):
        from custom_components.belgiantrain.sensor import async_setup_entry

        entities = []

        def mock_add_entities(entity_list):
            entities.extend(entity_list)

        await async_setup_entry(hass, mock_config_entry, mock_add_entities)

        # Should not create any entities if stations are not found
        assert len(entities) == 0


async def test_nmbs_sensor_update(hass: HomeAssistant, mock_stations):
    """Test BelgianTrainConnectionSensor update method."""
    # Create mock API client
    mock_api = AsyncMock()

    # Create mock connection data
    mock_departure = MagicMock()
    mock_departure.time = dt_util.utcnow()
    mock_departure.delay = 120  # 2 minutes delay in seconds
    mock_departure.left = False
    mock_departure.canceled = False
    mock_departure.station = "Brussels-South"
    mock_departure.direction = MagicMock(name="Ghent")
    mock_departure.platform = "3"
    mock_departure.vehicle = "IC1234"
    mock_departure.station_info = MagicMock(latitude="50.8465", longitude="4.3517")

    mock_arrival = MagicMock()
    mock_arrival.time = dt_util.utcnow()
    mock_arrival.platform = "7"

    mock_connection = MagicMock()
    mock_connection.departure = mock_departure
    mock_connection.arrival = mock_arrival
    mock_connection.vias = None

    mock_connections = MagicMock()
    mock_connections.connections = [mock_connection]

    mock_api.get_connections.return_value = mock_connections

    # Create sensor
    sensor = BelgianTrainConnectionSensor(
        mock_api,
        "Test Sensor",
        True,
        mock_stations[0],
        mock_stations[1],
        False,
    )

    # Update sensor
    await sensor.async_update()

    # Verify state is set (duration in minutes)
    assert sensor.native_value is not None
    assert isinstance(sensor.native_value, int)

    # Verify attributes
    attrs = sensor.extra_state_attributes
    assert attrs is not None
    assert "delay_minutes" in attrs
    assert attrs["delay_minutes"] == 2
    assert "departure_minutes" in attrs
    assert "platform_departing" in attrs
    assert attrs["platform_departing"] == "3"
    assert "vehicle_id" in attrs
    assert attrs["vehicle_id"] == "IC1234"


async def test_nmbs_sensor_with_via(hass: HomeAssistant, mock_stations):
    """Test BelgianTrainConnectionSensor with via connections."""
    mock_api = AsyncMock()

    # Create mock connection with via
    mock_departure = MagicMock()
    mock_departure.time = dt_util.utcnow()
    mock_departure.delay = 0
    mock_departure.left = False
    mock_departure.canceled = False
    mock_departure.station = "Brussels-Central"
    mock_departure.direction = MagicMock(name="Ghent")
    mock_departure.platform = "3"
    mock_departure.vehicle = "IC1234"
    mock_departure.station_info = MagicMock(latitude="50.8465", longitude="4.3517")

    mock_arrival = MagicMock()
    mock_arrival.time = dt_util.utcnow()
    mock_arrival.platform = "7"

    mock_via = MagicMock()
    mock_via.station = "Brussels-South"
    mock_via.arrival = MagicMock(platform="5")
    mock_via.departure = MagicMock(platform="6", delay=0)
    mock_via.timebetween = 300  # 5 minutes

    mock_connection = MagicMock()
    mock_connection.departure = mock_departure
    mock_connection.arrival = mock_arrival
    mock_connection.vias = [mock_via]

    mock_connections = MagicMock()
    mock_connections.connections = [mock_connection]

    mock_api.get_connections.return_value = mock_connections

    # Create sensor with exclude_vias=False
    sensor = BelgianTrainConnectionSensor(
        mock_api,
        "Test Sensor",
        False,
        mock_stations[0],
        mock_stations[1],
        False,
    )

    await sensor.async_update()

    # Verify via attributes are present
    attrs = sensor.extra_state_attributes
    assert "via" in attrs
    assert attrs["via"] == "Brussels-South"
    assert "via_arrival_platform" in attrs
    assert "via_transfer_platform" in attrs


async def test_nmbs_sensor_exclude_vias(hass: HomeAssistant, mock_stations):
    """Test BelgianTrainConnectionSensor with exclude_vias enabled."""
    mock_api = AsyncMock()

    # Create mock connection with via
    mock_departure = MagicMock()
    mock_departure.time = dt_util.utcnow()
    mock_departure.delay = 0
    mock_departure.left = False
    mock_departure.canceled = False

    mock_arrival = MagicMock()
    mock_arrival.time = dt_util.utcnow()

    mock_via = MagicMock()
    mock_connection = MagicMock()
    mock_connection.departure = mock_departure
    mock_connection.arrival = mock_arrival
    mock_connection.vias = [mock_via]

    mock_connections = MagicMock()
    mock_connections.connections = [mock_connection]

    mock_api.get_connections.return_value = mock_connections

    # Create sensor with exclude_vias=True
    sensor = BelgianTrainConnectionSensor(
        mock_api,
        "Test Sensor",
        False,
        mock_stations[0],
        mock_stations[1],
        True,  # exclude_vias
    )

    await sensor.async_update()

    # State should not be set when excluding via connections
    assert sensor.native_value is None


def test_get_time_until():
    """Test get_time_until function."""
    # Test with None
    assert get_time_until(None) == 0

    # Test with future time
    future_time = dt_util.utcnow().replace(microsecond=0) + dt_util.dt.timedelta(
        minutes=10
    )
    result = get_time_until(future_time)
    assert result == 10


def test_get_delay_in_minutes():
    """Test get_delay_in_minutes function."""
    assert get_delay_in_minutes(0) == 0
    assert get_delay_in_minutes(60) == 1
    assert get_delay_in_minutes(120) == 2
    assert get_delay_in_minutes(90) == 2  # rounds to 2


def test_get_ride_duration():
    """Test get_ride_duration function."""
    departure = dt_util.utcnow()
    arrival = departure + dt_util.dt.timedelta(minutes=30)

    # No delay
    duration = get_ride_duration(departure, arrival, 0)
    assert duration == 30

    # With 2 minute delay (120 seconds)
    duration = get_ride_duration(departure, arrival, 120)
    assert duration == 32


async def test_nmbs_sensor_connection_already_left(hass: HomeAssistant, mock_stations):
    """Test BelgianTrainConnectionSensor when first connection has already left."""
    mock_api = AsyncMock()

    # First connection has left
    mock_connection_1 = MagicMock()
    mock_connection_1.departure = MagicMock(left=True)

    # Second connection is available
    mock_departure_2 = MagicMock()
    mock_departure_2.time = dt_util.utcnow()
    mock_departure_2.delay = 0
    mock_departure_2.left = False
    mock_departure_2.canceled = False
    mock_departure_2.station = "Brussels-South"
    mock_departure_2.direction = MagicMock(name="Ghent")
    mock_departure_2.platform = "3"
    mock_departure_2.vehicle = "IC1234"
    mock_departure_2.station_info = MagicMock(latitude="50.8465", longitude="4.3517")

    mock_arrival_2 = MagicMock()
    mock_arrival_2.time = dt_util.utcnow()
    mock_arrival_2.platform = "7"

    mock_connection_2 = MagicMock()
    mock_connection_2.departure = mock_departure_2
    mock_connection_2.arrival = mock_arrival_2
    mock_connection_2.vias = None

    mock_connections = MagicMock()
    mock_connections.connections = [mock_connection_1, mock_connection_2]

    mock_api.get_connections.return_value = mock_connections

    sensor = BelgianTrainConnectionSensor(
        mock_api,
        "Test Sensor",
        False,
        mock_stations[0],
        mock_stations[1],
        False,
    )

    await sensor.async_update()

    # Should use second connection
    assert sensor.native_value is not None
    attrs = sensor.extra_state_attributes
    assert attrs["vehicle_id"] == "IC1234"


async def test_coordinator_access_via_runtime_data(
    hass: HomeAssistant, mock_stations, mock_config_entry
):
    """Test that sensor setup accesses coordinator via runtime_data."""
    # Set up domain data structure
    hass.data[DOMAIN] = {
        "stations": mock_stations,
        "coordinators": {},
    }

    # Create a mock coordinator
    mock_coordinator = MagicMock()
    mock_coordinator.data = {}

    # Create runtime_data with the coordinator
    from custom_components.belgiantrain.data import BelgianTrainData

    mock_runtime_data = BelgianTrainData(coordinator=mock_coordinator)
    mock_config_entry.runtime_data = mock_runtime_data
    mock_config_entry.entry_id = "test_entry_id"

    # Mock subentry_type attribute
    mock_config_entry.subentry_type = None

    from custom_components.belgiantrain.sensor import async_setup_entry

    entities = []

    def mock_add_entities(entity_list):
        entities.extend(entity_list)

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    # Should create entities using coordinator from runtime_data
    assert len(entities) == 3


async def test_coordinator_access_via_hass_data_fallback(
    hass: HomeAssistant, mock_stations, mock_config_entry
):
    """Test sensor setup falls back to hass.data when runtime_data unavailable."""
    # Create a mock coordinator
    mock_coordinator = MagicMock()
    mock_coordinator.data = {}

    # Set up domain data with coordinator in legacy location
    hass.data[DOMAIN] = {
        "stations": mock_stations,
        "coordinators": {"test_entry_id": mock_coordinator},
    }

    # Config entry without runtime_data (legacy mode)
    mock_config_entry.runtime_data = None
    mock_config_entry.entry_id = "test_entry_id"

    # Mock subentry_type attribute
    mock_config_entry.subentry_type = None

    from custom_components.belgiantrain.sensor import async_setup_entry

    entities = []

    def mock_add_entities(entity_list):
        entities.extend(entity_list)

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    # Should create entities using coordinator from hass.data
    assert len(entities) == 3


async def test_coordinator_not_found(
    hass: HomeAssistant, mock_stations, mock_config_entry
):
    """Test sensor setup when no coordinator is found in either location."""
    # Set up domain data without coordinator
    hass.data[DOMAIN] = {
        "stations": mock_stations,
        "coordinators": {},
    }

    # Config entry without runtime_data and no coordinator in hass.data
    mock_config_entry.runtime_data = None
    mock_config_entry.entry_id = "test_entry_id"

    # Mock subentry_type attribute
    mock_config_entry.subentry_type = None

    from custom_components.belgiantrain.sensor import async_setup_entry

    entities = []

    def mock_add_entities(entity_list):
        entities.extend(entity_list)

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    # Should not create any entities if coordinator is not found
    assert len(entities) == 0
