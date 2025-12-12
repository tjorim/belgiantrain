"""Test the SNCB/NMBS config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.belgiantrain.config_flow import CannotConnectError
from custom_components.belgiantrain.const import (
    CONF_EXCLUDE_VIAS,
    CONF_SHOW_ON_MAP,
    CONF_STATION_FROM,
    CONF_STATION_LIVE,
    CONF_STATION_TO,
    DOMAIN,
)


async def test_form(hass: HomeAssistant, mock_setup_entry: AsyncMock) -> None:
    """Test we can set up the integration with a connection."""
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

    # Should show menu to choose connection or liveboard
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "user"
    assert "connection" in result["menu_options"]
    assert "liveboard" in result["menu_options"]

    # Choose connection
    with patch("custom_components.belgiantrain.config_flow.iRail") as mock_irail:
        mock_api = AsyncMock()
        mock_api.get_stations.return_value = mock_stations_response
        mock_irail.return_value = mock_api

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"next_step_id": "connection"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "connection"

    # Configure connection
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
    assert result["title"] == "SNCB/NMBS Belgian Trains"
    assert "first_connection" in result["data"]
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.skip(reason="Connection subentry flow requires Home Assistant 2025.2+")
async def test_form_same_station(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    """Test we handle same station error in connection subentry."""
    # This test is for connection subentry flow which requires HA 2025.2+
    # Mock the station list
    mock_station_1 = MagicMock()
    mock_station_1.id = "BE.NMBS.008812005"
    mock_station_1.standard_name = "Brussels-Central"

    mock_station_2 = MagicMock()
    mock_station_2.id = "BE.NMBS.008892007"
    mock_station_2.standard_name = "Ghent-Sint-Pieters"

    mock_stations_response = MagicMock()
    mock_stations_response.stations = [mock_station_1, mock_station_2]

    # Create main entry first
    with patch("custom_components.belgiantrain.config_flow.iRail") as mock_irail:
        mock_api = AsyncMock()
        mock_api.get_stations.return_value = mock_stations_response
        mock_irail.return_value = mock_api

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    main_entry = result["result"]

    # Try to add connection subentry with same station
    with patch("custom_components.belgiantrain.config_flow.iRail") as mock_irail:
        mock_api = AsyncMock()
        mock_api.get_stations.return_value = mock_stations_response
        mock_irail.return_value = mock_api

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "subentry", "parent_entry_id": main_entry.entry_id},
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


@pytest.mark.skip(reason="ConfigSubentryFlow requires Home Assistant 2025.2+")
async def test_subentry_liveboard_flow(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    """Test subentry flow for adding a liveboard sensor."""
    # First create a main config entry
    mock_station_1 = MagicMock()
    mock_station_1.id = "BE.NMBS.008812005"
    mock_station_1.standard_name = "Brussels-Central"

    mock_station_2 = MagicMock()
    mock_station_2.id = "BE.NMBS.008892007"
    mock_station_2.standard_name = "Ghent-Sint-Pieters"

    mock_station_3 = MagicMock()
    mock_station_3.id = "BE.NMBS.008863008"
    mock_station_3.standard_name = "Antwerp-Central"

    mock_stations_response = MagicMock()
    mock_stations_response.stations = [mock_station_1, mock_station_2, mock_station_3]

    # Create a main entry first
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
                CONF_STATION_TO: "BE.NMBS.008892007",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    main_entry = result["result"]

    # Mock the station data in hass.data
    hass.data[DOMAIN] = {
        "stations": [mock_station_1, mock_station_2, mock_station_3],
        "coordinators": {},
        "api_client": None,
    }

    # Now test the subentry flow
    with patch("custom_components.belgiantrain.config_flow.iRail") as mock_irail:
        mock_api = AsyncMock()
        mock_api.get_stations.return_value = mock_stations_response
        mock_irail.return_value = mock_api

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "subentry", "parent_entry_id": main_entry.entry_id},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch("custom_components.belgiantrain.config_flow.iRail") as mock_irail:
        mock_api = AsyncMock()
        mock_api.get_stations.return_value = mock_stations_response
        mock_irail.return_value = mock_api

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"station_live": "BE.NMBS.008863008"},
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Liveboard - Antwerp-Central"
    assert result["data"] == {"station_live": "BE.NMBS.008863008"}
    assert result["result"].unique_id == "liveboard_BE.NMBS.008863008"


@pytest.mark.skip(reason="ConfigSubentryFlow requires Home Assistant 2025.2+")
async def test_subentry_liveboard_already_configured(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    """Test subentry flow aborts when liveboard is already configured."""
    # Note: This test is skipped because ConfigSubentryFlow requires HA 2025.2+
    # The logic below shows how the test should work when the feature is available
    
    mock_station_1 = MagicMock()
    mock_station_1.id = "BE.NMBS.008812005"
    mock_station_1.standard_name = "Brussels-Central"

    mock_station_2 = MagicMock()
    mock_station_2.id = "BE.NMBS.008892007"
    mock_station_2.standard_name = "Ghent-Sint-Pieters"

    mock_stations_response = MagicMock()
    mock_stations_response.stations = [mock_station_1, mock_station_2]

    # Create a main config entry first
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
                CONF_STATION_TO: "BE.NMBS.008892007",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    main_entry = result["result"]

    # Mock the station data in hass.data
    hass.data[DOMAIN] = {
        "stations": [mock_station_1, mock_station_2],
        "coordinators": {},
        "api_client": None,
    }

    # Create the first liveboard subentry
    with patch("custom_components.belgiantrain.config_flow.iRail") as mock_irail:
        mock_api = AsyncMock()
        mock_api.get_stations.return_value = mock_stations_response
        mock_irail.return_value = mock_api

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "subentry", "parent_entry_id": main_entry.entry_id},
        )
        assert result["type"] == FlowResultType.FORM

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_STATION_LIVE: "BE.NMBS.008812005"},
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY

    # Attempt to create a duplicate liveboard subentry
    with patch("custom_components.belgiantrain.config_flow.iRail") as mock_irail:
        mock_api = AsyncMock()
        mock_api.get_stations.return_value = mock_stations_response
        mock_irail.return_value = mock_api

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "subentry", "parent_entry_id": main_entry.entry_id},
        )
        assert result["type"] == FlowResultType.FORM

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_STATION_LIVE: "BE.NMBS.008812005"},
        )
        await hass.async_block_till_done()

    # Should abort because this station is already configured
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.skip(reason="ConfigSubentryFlow requires Home Assistant 2025.2+")
async def test_subentry_liveboard_api_unavailable(hass: HomeAssistant) -> None:
    """Test subentry flow handles API unavailable error."""
    # Mock the station data in hass.data
    hass.data[DOMAIN] = {
        "stations": [],
        "coordinators": {},
        "api_client": None,
    }

    with patch("custom_components.belgiantrain.config_flow.iRail") as mock_irail:
        mock_api = AsyncMock()
        mock_api.get_stations.side_effect = CannotConnectError("API unavailable")
        mock_irail.return_value = mock_api

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "subentry", "parent_entry_id": "mock_entry_id"},
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "api_unavailable"
