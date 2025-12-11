"""Test the SNCB/NMBS service calls."""

from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.belgiantrain import async_setup
from custom_components.belgiantrain.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import ServiceCall


async def test_get_disturbances_service(hass: HomeAssistant) -> None:
    """Test the get_disturbances service."""
    # Mock the API response
    mock_disturbance = MagicMock()
    mock_disturbance.id = "1"
    mock_disturbance.title = "Delay on line Brussels-Ghent"
    mock_disturbance.description = "Train delayed by 15 minutes"
    mock_disturbance.type = "delay"
    mock_disturbance.timestamp = datetime(2024, 12, 11, 10, 30)

    mock_disturbances = MagicMock()
    mock_disturbances.disturbances = [mock_disturbance]

    with patch("custom_components.belgiantrain.iRail") as mock_irail:
        mock_api = AsyncMock()
        mock_api.get_stations.return_value = MagicMock(stations=[])
        mock_api.get_disturbances.return_value = mock_disturbances
        mock_irail.return_value = mock_api

        # Set up the integration
        assert await async_setup(hass, {})

        # Call the service
        response = await hass.services.async_call(
            DOMAIN,
            "get_disturbances",
            {},
            blocking=True,
            return_response=True,
        )

        # Verify response
        assert response is not None
        assert "disturbances" in response
        assert len(response["disturbances"]) == 1
        assert response["disturbances"][0]["id"] == "1"
        assert response["disturbances"][0]["title"] == "Delay on line Brussels-Ghent"
        assert response["disturbances"][0]["type"] == "delay"


async def test_get_disturbances_service_no_disturbances(hass: HomeAssistant) -> None:
    """Test the get_disturbances service when no disturbances exist."""
    with patch("custom_components.belgiantrain.iRail") as mock_irail:
        mock_api = AsyncMock()
        mock_api.get_stations.return_value = MagicMock(stations=[])
        mock_api.get_disturbances.return_value = None
        mock_irail.return_value = mock_api

        # Set up the integration
        assert await async_setup(hass, {})

        # Call the service
        response = await hass.services.async_call(
            DOMAIN,
            "get_disturbances",
            {},
            blocking=True,
            return_response=True,
        )

        # Verify response
        assert response is not None
        assert "disturbances" in response
        assert len(response["disturbances"]) == 0


async def test_get_vehicle_service(hass: HomeAssistant) -> None:
    """Test the get_vehicle service."""
    # Mock the API response
    mock_stop = MagicMock()
    mock_stop.station = "Brussels-Central"
    mock_stop.platform = "3"
    mock_stop.time = datetime(2024, 12, 11, 10, 30)
    mock_stop.delay = 0
    mock_stop.canceled = False

    mock_vehicle = MagicMock()
    mock_vehicle.vehicle = "BE.NMBS.IC1832"
    mock_vehicle.name = "IC 1832"
    mock_vehicle.stops = [mock_stop]

    with patch("custom_components.belgiantrain.iRail") as mock_irail:
        mock_api = AsyncMock()
        mock_api.get_stations.return_value = MagicMock(stations=[])
        mock_api.get_vehicle.return_value = mock_vehicle
        mock_irail.return_value = mock_api

        # Set up the integration
        assert await async_setup(hass, {})

        # Call the service
        response = await hass.services.async_call(
            DOMAIN,
            "get_vehicle",
            {"vehicle_id": "BE.NMBS.IC1832"},
            blocking=True,
            return_response=True,
        )

        # Verify response
        assert response is not None
        assert response["vehicle_id"] == "BE.NMBS.IC1832"
        assert response["name"] == "IC 1832"
        assert len(response["stops"]) == 1
        assert response["stops"][0]["station"] == "Brussels-Central"
        assert response["stops"][0]["platform"] == "3"


async def test_get_vehicle_service_not_found(hass: HomeAssistant) -> None:
    """Test the get_vehicle service when vehicle is not found."""
    with patch("custom_components.belgiantrain.iRail") as mock_irail:
        mock_api = AsyncMock()
        mock_api.get_stations.return_value = MagicMock(stations=[])
        mock_api.get_vehicle.return_value = None
        mock_irail.return_value = mock_api

        # Set up the integration
        assert await async_setup(hass, {})

        # Call the service
        response = await hass.services.async_call(
            DOMAIN,
            "get_vehicle",
            {"vehicle_id": "BE.NMBS.INVALID"},
            blocking=True,
            return_response=True,
        )

        # Verify response
        assert response is not None
        assert response["vehicle_id"] == "BE.NMBS.INVALID"
        assert "error" in response
