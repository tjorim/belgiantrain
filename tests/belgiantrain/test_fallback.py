"""Test fallback behavior for Home Assistant < 2025.2."""

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.belgiantrain import async_setup_entry
from custom_components.belgiantrain.const import (
    CONF_EXCLUDE_VIAS,
    CONF_STATION_FROM,
    CONF_STATION_TO,
    DOMAIN,
)


async def test_connection_fallback_for_old_ha_versions(hass: HomeAssistant) -> None:
    """Test that connections work on Home Assistant < 2025.2."""
    # Mock station data
    mock_station_1 = MagicMock()
    mock_station_1.id = "BE.NMBS.008812005"
    mock_station_1.standard_name = "Brussels-Central"
    mock_station_1.name = "Brussels-Central"
    mock_station_1.latitude = "50.845466"
    mock_station_1.longitude = "4.357181"

    mock_station_2 = MagicMock()
    mock_station_2.id = "BE.NMBS.008892007"
    mock_station_2.standard_name = "Ghent-Sint-Pieters"
    mock_station_2.name = "Ghent-Sint-Pieters"
    mock_station_2.latitude = "51.035896"
    mock_station_2.longitude = "3.710675"

    # Set up hass.data with station data
    hass.data[DOMAIN] = {
        "stations": [mock_station_1, mock_station_2],
        "coordinators": {},
    }

    # Mock the ConfigSubentry as None to simulate HA < 2025.2
    with patch(
        "custom_components.belgiantrain._ConfigSubentry", None
    ), patch.object(
        hass.config_entries, "async_forward_entry_setups"
    ) as mock_forward_setups:
        # Create a config entry with initial connection data
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="SNCB/NMBS Belgian Trains",
            data={
                "first_connection": {
                    CONF_STATION_FROM: "BE.NMBS.008812005",
                    CONF_STATION_TO: "BE.NMBS.008892007",
                    CONF_EXCLUDE_VIAS: False,
                }
            },
            unique_id=DOMAIN,
        )
        entry.add_to_hass(hass)

        # Mock the API calls
        mock_connections = MagicMock()
        mock_connections.connections = [MagicMock()]
        mock_liveboard = MagicMock()
        mock_liveboard.departures = [MagicMock()]

        with patch("custom_components.belgiantrain.iRail") as mock_irail:
            mock_api = AsyncMock()
            mock_api.get_connections.return_value = mock_connections
            mock_api.get_liveboard.return_value = mock_liveboard
            mock_irail.return_value = mock_api

            # Run setup
            result = await async_setup_entry(hass, entry)

            # Verify setup succeeded
            assert result is True

            # Verify platforms were set up for the main entry (fallback behavior)
            mock_forward_setups.assert_called_once()

            # Verify coordinator was created
            assert entry.entry_id in hass.data[DOMAIN]["coordinators"]

            # Verify entry data was updated with connection details
            assert CONF_STATION_FROM in entry.data
            assert CONF_STATION_TO in entry.data


async def test_liveboard_fallback_for_old_ha_versions(hass: HomeAssistant) -> None:
    """Test that liveboards work on Home Assistant < 2025.2."""
    # Mock station data
    mock_station = MagicMock()
    mock_station.id = "BE.NMBS.008812005"
    mock_station.standard_name = "Brussels-Central"
    mock_station.name = "Brussels-Central"

    # Set up hass.data with station data
    hass.data[DOMAIN] = {
        "stations": [mock_station],
        "coordinators": {},
    }

    # Mock the ConfigSubentry as None to simulate HA < 2025.2
    with patch(
        "custom_components.belgiantrain._ConfigSubentry", None
    ), patch.object(
        hass.config_entries, "async_forward_entry_setups"
    ) as mock_forward_setups:
        # Create a config entry with initial liveboard data
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="SNCB/NMBS Belgian Trains",
            data={"first_liveboard": {"station_live": "BE.NMBS.008812005"}},
            unique_id=DOMAIN,
        )
        entry.add_to_hass(hass)

        # Mock the API calls
        mock_liveboard = MagicMock()
        mock_liveboard.departures = [MagicMock()]

        with patch("custom_components.belgiantrain.iRail") as mock_irail:
            mock_api = AsyncMock()
            mock_api.get_liveboard.return_value = mock_liveboard
            mock_irail.return_value = mock_api

            # Run setup
            result = await async_setup_entry(hass, entry)

            # Verify setup succeeded
            assert result is True

            # Verify platforms were set up for the main entry (fallback behavior)
            mock_forward_setups.assert_called_once()

            # Verify coordinator was created
            assert entry.entry_id in hass.data[DOMAIN]["coordinators"]

            # Verify entry data was updated with liveboard details
            assert "station_live" in entry.data
