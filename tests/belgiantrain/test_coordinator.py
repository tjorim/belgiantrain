"""Test the SNCB/NMBS coordinator."""

# ruff: noqa: ANN001, ANN201, ANN202, ARG001

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.belgiantrain.coordinator import BelgianTrainDataUpdateCoordinator


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
def mock_api_client():
    """Create a mock API client."""
    return AsyncMock()


async def test_coordinator_update_success(
    hass: HomeAssistant, mock_api_client, mock_stations
):
    """Test successful coordinator data update."""
    # Mock API responses
    mock_connections = MagicMock()
    mock_connections.connections = []

    mock_liveboard_from = MagicMock()
    mock_liveboard_from.departures = []

    mock_liveboard_to = MagicMock()
    mock_liveboard_to.departures = []

    mock_api_client.get_connections.return_value = mock_connections
    mock_api_client.get_liveboard.side_effect = [mock_liveboard_from, mock_liveboard_to]

    # Create coordinator
    coordinator = BelgianTrainDataUpdateCoordinator(
        hass, mock_api_client, mock_stations[0], mock_stations[1]
    )

    # Update data
    await coordinator.async_refresh()

    # Verify data is populated
    assert coordinator.data is not None
    assert "connections" in coordinator.data
    assert "liveboard_from" in coordinator.data
    assert "liveboard_to" in coordinator.data
    assert coordinator.data["connections"] == mock_connections
    assert coordinator.data["liveboard_from"] == mock_liveboard_from
    assert coordinator.data["liveboard_to"] == mock_liveboard_to

    # Verify API was called correctly
    mock_api_client.get_connections.assert_called_once_with(
        mock_stations[0].id, mock_stations[1].id
    )
    assert mock_api_client.get_liveboard.call_count == 2


async def test_coordinator_update_connection_failure(
    hass: HomeAssistant, mock_api_client, mock_stations
):
    """Test coordinator when connection data is None."""
    # Mock API to return None for connections
    mock_api_client.get_connections.return_value = None

    # Create coordinator
    coordinator = BelgianTrainDataUpdateCoordinator(
        hass, mock_api_client, mock_stations[0], mock_stations[1]
    )

    # Update should raise UpdateFailed
    with pytest.raises(UpdateFailed, match="Failed to fetch connection data"):
        await coordinator.async_refresh()


async def test_coordinator_update_api_exception(
    hass: HomeAssistant, mock_api_client, mock_stations
):
    """Test coordinator when API raises exception."""
    # Mock API to raise exception
    mock_api_client.get_connections.side_effect = Exception("API Error")

    # Create coordinator
    coordinator = BelgianTrainDataUpdateCoordinator(
        hass, mock_api_client, mock_stations[0], mock_stations[1]
    )

    # Update should raise UpdateFailed
    with pytest.raises(UpdateFailed, match="Error communicating with iRail API"):
        await coordinator.async_refresh()


async def test_coordinator_stores_correct_stations(
    hass: HomeAssistant, mock_api_client, mock_stations
):
    """Test that coordinator stores the correct station references."""
    coordinator = BelgianTrainDataUpdateCoordinator(
        hass, mock_api_client, mock_stations[0], mock_stations[1]
    )

    assert coordinator.station_from == mock_stations[0]
    assert coordinator.station_to == mock_stations[1]
    assert coordinator.api_client == mock_api_client
