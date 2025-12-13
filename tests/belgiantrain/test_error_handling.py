"""Test error handling scenarios for the SNCB/NMBS integration."""

# ruff: noqa: ANN001, PLC0415, SLF001

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.belgiantrain.const import (
    CONF_EXCLUDE_VIAS,
    CONF_STATION_FROM,
    CONF_STATION_LIVE,
    CONF_STATION_TO,
    DOMAIN,
)


async def test_async_setup_api_failure(hass: HomeAssistant) -> None:
    """Test that async_setup returns False when API fails to fetch stations."""
    with patch("custom_components.belgiantrain.iRail") as mock_irail:
        mock_api = AsyncMock()
        # Simulate API returning None (failure)
        mock_api.get_stations.return_value = None
        mock_irail.return_value = mock_api

        from custom_components.belgiantrain import async_setup

        result = await async_setup(hass, {})

        # Should return False when API fails
        assert not result


async def test_async_setup_entry_missing_station_data(hass: HomeAssistant) -> None:
    """Test that async_setup_entry returns False when station data is missing."""
    # Don't populate hass.data[DOMAIN] with stations
    hass.data[DOMAIN] = {}  # Missing 'stations' key

    mock_entry = MagicMock(spec=ConfigEntry)
    mock_entry.data = {
        CONF_STATION_FROM: "BE.NMBS.008812005",
        CONF_STATION_TO: "BE.NMBS.008892007",
        CONF_EXCLUDE_VIAS: False,
    }
    mock_entry.entry_id = "test_entry"

    from custom_components.belgiantrain import async_setup_entry

    result = await async_setup_entry(hass, mock_entry)

    # Should return False when station data is missing
    assert result is False


async def test_async_setup_entry_invalid_station_data(hass: HomeAssistant) -> None:
    """Test that async_setup_entry returns False when station data is invalid."""
    # Set invalid station data (not a dict)
    hass.data[DOMAIN] = "invalid_data"

    mock_entry = MagicMock(spec=ConfigEntry)
    mock_entry.data = {
        CONF_STATION_FROM: "BE.NMBS.008812005",
        CONF_STATION_TO: "BE.NMBS.008892007",
        CONF_EXCLUDE_VIAS: False,
    }
    mock_entry.entry_id = "test_entry"

    from custom_components.belgiantrain import async_setup_entry

    result = await async_setup_entry(hass, mock_entry)

    # Should return False when station data is invalid
    assert result is False


async def test_coordinator_raises_update_failed_on_connection_error(
    hass: HomeAssistant, mock_stations
) -> None:
    """Test coordinator raises UpdateFailed when API returns None."""
    hass.data[DOMAIN] = {"stations": mock_stations, "coordinators": {}}

    mock_api = AsyncMock()
    # Simulate API returning None (connection error)
    mock_api.get_connections.return_value = None
    # Mock other required API calls
    mock_api.get_liveboard.return_value = AsyncMock()

    from custom_components.belgiantrain.coordinator import (
        BelgianTrainDataUpdateCoordinator,
    )

    coordinator = BelgianTrainDataUpdateCoordinator(
        hass,
        api_client=mock_api,
        station_from=mock_stations[0],
        station_to=mock_stations[1],
    )

    # Should raise UpdateFailed when API returns None
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_coordinator_raises_update_failed_on_liveboard_error(
    hass: HomeAssistant, mock_stations
) -> None:
    """Test that coordinator raises UpdateFailed when API returns None for liveboard."""
    hass.data[DOMAIN] = {"stations": mock_stations, "coordinators": {}}

    mock_api = AsyncMock()
    # Simulate API returning None (liveboard error)
    mock_api.get_liveboard.return_value = None

    from custom_components.belgiantrain.coordinator import (
        LiveboardDataUpdateCoordinator,
    )

    coordinator = LiveboardDataUpdateCoordinator(
        hass,
        api_client=mock_api,
        station=mock_stations[0],
    )

    # Should raise UpdateFailed when API returns None
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_coordinator_raises_update_failed_on_api_exception(
    hass: HomeAssistant, mock_stations
) -> None:
    """Test that coordinator raises UpdateFailed when API raises an exception."""
    hass.data[DOMAIN] = {"stations": mock_stations, "coordinators": {}}

    mock_api = AsyncMock()
    # Simulate API raising an exception
    mock_api.get_connections.side_effect = Exception("API error")

    from custom_components.belgiantrain.coordinator import (
        BelgianTrainDataUpdateCoordinator,
    )

    coordinator = BelgianTrainDataUpdateCoordinator(
        hass,
        api_client=mock_api,
        station_from=mock_stations[0],
        station_to=mock_stations[1],
    )

    # Should raise UpdateFailed when API raises exception
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_async_setup_entry_same_station_error(
    hass: HomeAssistant, mock_stations
) -> None:
    """Test async_setup_entry returns False with same station."""
    # Initialize station data properly
    hass.data[DOMAIN] = {
        "stations": mock_stations,
        "coordinators": {},
        "api_client": AsyncMock(),
    }

    mock_entry = MagicMock(spec=ConfigEntry)
    # Create connection data with same station for from and to
    mock_entry.data = {
        "first_connection": {
            CONF_STATION_FROM: "BE.NMBS.008812005",
            CONF_STATION_TO: "BE.NMBS.008812005",  # Same as FROM
            CONF_EXCLUDE_VIAS: False,
        }
    }
    mock_entry.entry_id = "test_entry"
    mock_entry.runtime_data = None
    mock_entry.subentry_type = None

    from custom_components.belgiantrain import async_setup_entry

    result = await async_setup_entry(hass, mock_entry)

    # Should return False when from and to stations are the same
    assert result is False


async def test_service_get_disturbances_handles_exception(hass: HomeAssistant) -> None:
    """Test that get_disturbances service handles exceptions gracefully."""
    # Setup integration with mocked API
    mock_api = AsyncMock()
    # Simulate API raising an exception
    mock_api.get_disturbances.side_effect = Exception("API connection error")

    # Mock the station fetch to succeed
    mock_stations_response = MagicMock()
    mock_stations_response.stations = []
    mock_api.get_stations.return_value = mock_stations_response

    # Import and setup services
    from custom_components.belgiantrain import async_setup

    # Mock iRail creation to return our mocked API
    with patch("custom_components.belgiantrain.iRail") as mock_irail:
        mock_irail.return_value = mock_api
        await async_setup(hass, {})

    # Call the service
    result = await hass.services.async_call(
        DOMAIN, "get_disturbances", {}, blocking=True, return_response=True
    )

    # Should return empty disturbances list and error message
    assert "disturbances" in result
    assert result["disturbances"] == []
    assert "error" in result


async def test_service_get_vehicle_handles_not_found(hass: HomeAssistant) -> None:
    """Test that get_vehicle service handles vehicle not found gracefully."""
    # Setup integration with mocked API
    mock_api = AsyncMock()
    # Simulate API returning None (vehicle not found)
    mock_api.get_vehicle.return_value = None

    # Mock the station fetch to succeed
    mock_stations_response = MagicMock()
    mock_stations_response.stations = []
    mock_api.get_stations.return_value = mock_stations_response

    # Import and setup services
    from custom_components.belgiantrain import async_setup

    # Mock iRail creation to return our mocked API
    with patch("custom_components.belgiantrain.iRail") as mock_irail:
        mock_irail.return_value = mock_api
        await async_setup(hass, {})

    # Call the service
    result = await hass.services.async_call(
        DOMAIN,
        "get_vehicle",
        {"vehicle_id": "IC1234"},
        blocking=True,
        return_response=True,
    )

    # Should return error message
    assert "vehicle_id" in result
    assert "error" in result
    assert result["error"] == "Vehicle not found or API error"


async def test_async_setup_entry_station_not_found(
    hass: HomeAssistant, mock_stations
) -> None:
    """Test that async_setup_entry returns False when station not found."""
    from custom_components.belgiantrain.const import SUBENTRY_TYPE_CONNECTION

    # Initialize station data properly with stations
    hass.data[DOMAIN] = {
        "stations": mock_stations,
        "coordinators": {},
        "api_client": AsyncMock(),
    }

    mock_entry = MagicMock(spec=ConfigEntry)
    # Create connection subentry data with non-existent station ID
    mock_entry.data = {
        CONF_STATION_FROM: "BE.NMBS.999999999",  # Non-existent station
        CONF_STATION_TO: "BE.NMBS.008892007",
        CONF_EXCLUDE_VIAS: False,
    }
    mock_entry.entry_id = "test_entry"
    mock_entry.runtime_data = None
    mock_entry.subentry_type = SUBENTRY_TYPE_CONNECTION

    from custom_components.belgiantrain import async_setup_entry

    # Should return False when station is not found for connection subentry
    result = await async_setup_entry(hass, mock_entry)

    # Should return False when station not found
    assert result is False


async def test_async_setup_entry_liveboard_station_not_found(
    hass: HomeAssistant, mock_stations
) -> None:
    """Test that async_setup_entry returns False when liveboard station not found."""
    from custom_components.belgiantrain.const import SUBENTRY_TYPE_LIVEBOARD

    # Initialize station data properly with stations
    hass.data[DOMAIN] = {
        "stations": mock_stations,
        "coordinators": {},
        "api_client": AsyncMock(),
    }

    mock_entry = MagicMock(spec=ConfigEntry)
    # Create liveboard subentry data with non-existent station ID
    mock_entry.data = {
        CONF_STATION_LIVE: "BE.NMBS.999999999",  # Non-existent station
    }
    mock_entry.entry_id = "test_entry"
    mock_entry.runtime_data = None
    mock_entry.subentry_type = SUBENTRY_TYPE_LIVEBOARD

    from custom_components.belgiantrain import async_setup_entry

    # Should return False when station is not found for liveboard subentry
    result = await async_setup_entry(hass, mock_entry)

    # Should return False when station not found
    assert result is False
