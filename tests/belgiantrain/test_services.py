"""Test the SNCB/NMBS service calls."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.belgiantrain import async_setup
from custom_components.belgiantrain.const import DOMAIN


async def test_get_disturbances_service(hass: HomeAssistant) -> None:
    """Test the get_disturbances service."""
    # Mock the API response
    mock_disturbance = MagicMock()
    mock_disturbance.id = "1"
    mock_disturbance.title = "Delay on line Brussels-Ghent"
    mock_disturbance.description = "Train delayed by 15 minutes"
    mock_disturbance.type = "delay"
    mock_disturbance.timestamp = datetime(2024, 12, 11, 10, 30, tzinfo=UTC)

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
    mock_stop.time = datetime(2024, 12, 11, 10, 30, tzinfo=UTC)
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


async def test_get_composition_service(hass: HomeAssistant) -> None:
    """Test the get_composition service."""
    # Mock the API response
    mock_unit = MagicMock()
    mock_unit.material_type = "M6"
    mock_unit.has_toilet = True
    mock_unit.has_bike_section = False
    mock_unit.has_prmSection = True

    mock_composition_units = MagicMock()
    mock_composition_units.units = [mock_unit]

    mock_segment = MagicMock()
    mock_segment.origin = "Brussels"
    mock_segment.destination = "Ghent"
    mock_segment.composition = mock_composition_units

    mock_composition_data = MagicMock()
    mock_composition_data.segments = [mock_segment]

    mock_composition = MagicMock()
    mock_composition.composition = mock_composition_data

    with patch("custom_components.belgiantrain.iRail") as mock_irail:
        mock_api = AsyncMock()
        mock_api.get_stations.return_value = MagicMock(stations=[])
        mock_api.get_composition.return_value = mock_composition
        mock_irail.return_value = mock_api

        # Set up the integration
        assert await async_setup(hass, {})

        # Call the service
        response = await hass.services.async_call(
            DOMAIN,
            "get_composition",
            {"train_id": "S51507"},
            blocking=True,
            return_response=True,
        )

        # Verify response
        assert response is not None
        assert response["train_id"] == "S51507"
        assert "segments" in response
        assert len(response["segments"]) == 1
        assert response["segments"][0]["origin"] == "Brussels"
        assert response["segments"][0]["destination"] == "Ghent"


async def test_get_composition_service_not_found(hass: HomeAssistant) -> None:
    """Test the get_composition service when composition is not found."""
    with patch("custom_components.belgiantrain.iRail") as mock_irail:
        mock_api = AsyncMock()
        mock_api.get_stations.return_value = MagicMock(stations=[])
        mock_api.get_composition.return_value = None
        mock_irail.return_value = mock_api

        # Set up the integration
        assert await async_setup(hass, {})

        # Call the service
        response = await hass.services.async_call(
            DOMAIN,
            "get_composition",
            {"train_id": "INVALID"},
            blocking=True,
            return_response=True,
        )

        # Verify response
        assert response is not None
        assert response["train_id"] == "INVALID"
        assert "error" in response


async def test_get_stations_service(hass: HomeAssistant) -> None:
    """Test the get_stations service."""
    # Mock station data
    mock_station_1 = MagicMock()
    mock_station_1.id = "BE.NMBS.008812005"
    mock_station_1.name = "Brussels-Central"
    mock_station_1.standard_name = "Brussels-Central"
    mock_station_1.latitude = "50.845"
    mock_station_1.longitude = "4.357"

    mock_station_2 = MagicMock()
    mock_station_2.id = "BE.NMBS.008892007"
    mock_station_2.name = "Ghent-Sint-Pieters"
    mock_station_2.standard_name = "Ghent-Sint-Pieters"
    mock_station_2.latitude = "51.035"
    mock_station_2.longitude = "3.710"

    mock_stations = [mock_station_1, mock_station_2]

    with patch("custom_components.belgiantrain.iRail") as mock_irail:
        mock_api = AsyncMock()
        mock_api.get_stations.return_value = MagicMock(stations=mock_stations)
        mock_irail.return_value = mock_api

        # Set up the integration
        assert await async_setup(hass, {})

        # Call the service without filter
        response = await hass.services.async_call(
            DOMAIN,
            "get_stations",
            {},
            blocking=True,
            return_response=True,
        )

        # Verify response
        assert response is not None
        assert "stations" in response
        expected_count = len(mock_stations)
        assert response["count"] == expected_count
        assert len(response["stations"]) == expected_count


async def test_get_stations_service_with_filter(hass: HomeAssistant) -> None:
    """Test the get_stations service with name filter."""
    # Mock station data
    mock_station_1 = MagicMock()
    mock_station_1.id = "BE.NMBS.008812005"
    mock_station_1.name = "Brussels-Central"
    mock_station_1.standard_name = "Brussels-Central"
    mock_station_1.latitude = "50.845"
    mock_station_1.longitude = "4.357"

    mock_station_2 = MagicMock()
    mock_station_2.id = "BE.NMBS.008892007"
    mock_station_2.name = "Ghent-Sint-Pieters"
    mock_station_2.standard_name = "Ghent-Sint-Pieters"
    mock_station_2.latitude = "51.035"
    mock_station_2.longitude = "3.710"

    with patch("custom_components.belgiantrain.iRail") as mock_irail:
        mock_api = AsyncMock()
        mock_api.get_stations.return_value = MagicMock(
            stations=[mock_station_1, mock_station_2]
        )
        mock_irail.return_value = mock_api

        # Set up the integration
        assert await async_setup(hass, {})

        # Call the service with filter
        response = await hass.services.async_call(
            DOMAIN,
            "get_stations",
            {"name_filter": "Brussels"},
            blocking=True,
            return_response=True,
        )

        # Verify response
        assert response is not None
        assert "stations" in response
        assert response["count"] == 1
        assert len(response["stations"]) == 1
        assert response["stations"][0]["name"] == "Brussels-Central"
