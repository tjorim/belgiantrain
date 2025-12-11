"""Test the SNCB/NMBS config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.belgiantrain.config_flow import CannotConnectError
from custom_components.belgiantrain.const import (
    CONF_EXCLUDE_VIAS,
    CONF_SHOW_ON_MAP,
    CONF_STATION_FROM,
    CONF_STATION_TO,
    DOMAIN,
)

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


async def test_form(hass: HomeAssistant, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form."""
    # Mock the station list
    mock_station_1 = MagicMock()
    mock_station_1.id = "BE.NMBS.008812005"
    mock_station_1.standard_name = "Brussels-Central"

    mock_station_2 = MagicMock()
    mock_station_2.id = "BE.NMBS.008892007"
    mock_station_2.standard_name = "Ghent-Sint-Pieters"

    mock_stations_response = MagicMock()
    mock_stations_response.stations = [mock_station_1, mock_station_2]

    with patch("custom_components.belgiantrain.config_flow.iRail") as mock_irail:
        mock_api = AsyncMock()
        mock_api.get_stations.return_value = mock_stations_response
        mock_irail.return_value = mock_api

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}

    with patch("custom_components.belgiantrain.config_flow.iRail") as mock_irail:
        mock_api = AsyncMock()
        mock_api.get_stations.return_value = mock_stations_response
        mock_irail.return_value = mock_api

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_STATION_FROM: "BE.NMBS.008812005",
                CONF_STATION_TO: "BE.NMBS.008892007",
                CONF_EXCLUDE_VIAS: False,
                CONF_SHOW_ON_MAP: True,
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Train from Brussels-Central to Ghent-Sint-Pieters"
    assert result["data"] == {
        CONF_STATION_FROM: "BE.NMBS.008812005",
        CONF_STATION_TO: "BE.NMBS.008892007",
        CONF_EXCLUDE_VIAS: False,
        CONF_SHOW_ON_MAP: True,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_same_station(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    """Test we handle same station error."""
    # Mock the station list
    mock_station_1 = MagicMock()
    mock_station_1.id = "BE.NMBS.008812005"
    mock_station_1.standard_name = "Brussels-Central"

    mock_station_2 = MagicMock()
    mock_station_2.id = "BE.NMBS.008892007"
    mock_station_2.standard_name = "Ghent-Sint-Pieters"

    mock_stations_response = MagicMock()
    mock_stations_response.stations = [mock_station_1, mock_station_2]

    with patch("custom_components.belgiantrain.config_flow.iRail") as mock_irail:
        mock_api = AsyncMock()
        mock_api.get_stations.return_value = mock_stations_response
        mock_irail.return_value = mock_api

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_STATION_FROM: "BE.NMBS.008812005",
                CONF_STATION_TO: "BE.NMBS.008812005",
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "same_station"}

    # Make sure the config flow tests finish with either an
    # FlowResultType.CREATE_ENTRY or FlowResultType.ABORT so
    # we can show the config flow is able to recover from an error.
    with patch("custom_components.belgiantrain.config_flow.iRail") as mock_irail:
        mock_api = AsyncMock()
        mock_api.get_stations.return_value = mock_stations_response
        mock_irail.return_value = mock_api

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_STATION_FROM: "BE.NMBS.008812005",
                CONF_STATION_TO: "BE.NMBS.008892007",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Train from Brussels-Central to Ghent-Sint-Pieters"
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_api_unavailable(hass: HomeAssistant) -> None:
    """Test we handle API unavailable error."""
    with patch("custom_components.belgiantrain.config_flow.iRail") as mock_irail:
        mock_api = AsyncMock()
        mock_api.get_stations.side_effect = CannotConnectError("API unavailable")
        mock_irail.return_value = mock_api

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "api_unavailable"
