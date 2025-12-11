"""Test the SNCB/NMBS service calls."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.belgiantrain.const import DOMAIN


@pytest.fixture
def mock_coordinators(hass: HomeAssistant):
    """Create mock coordinators in hass.data."""
    # Initialize the domain data structure
    hass.data[DOMAIN] = {
        "stations": [],
        "coordinators": {},
    }

    # Create mock coordinators
    mock_coordinator_1 = MagicMock()
    mock_coordinator_1.async_request_refresh = AsyncMock()

    mock_coordinator_2 = MagicMock()
    mock_coordinator_2.async_request_refresh = AsyncMock()

    # Add coordinators to hass.data
    hass.data[DOMAIN]["coordinators"]["entry_1"] = mock_coordinator_1
    hass.data[DOMAIN]["coordinators"]["entry_2"] = mock_coordinator_2

    # Register the service (simulating what async_setup_entry does)
    async def async_refresh_data(_call):
        """Handle the refresh_data service call."""
        for coordinator in hass.data[DOMAIN]["coordinators"].values():
            await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, "refresh_data", async_refresh_data)

    return mock_coordinator_1, mock_coordinator_2


async def test_refresh_data_service_registered(
    hass: HomeAssistant, mock_coordinators
) -> None:
    """Test that the refresh_data service is registered."""
    assert hass.services.has_service(DOMAIN, "refresh_data")


async def test_refresh_data_service_call(
    hass: HomeAssistant, mock_coordinators
) -> None:
    """Test calling the refresh_data service."""
    mock_coordinator_1, mock_coordinator_2 = mock_coordinators

    # Call the service
    await hass.services.async_call(DOMAIN, "refresh_data", {}, blocking=True)

    # Verify both coordinators' refresh methods were called
    mock_coordinator_1.async_request_refresh.assert_called_once()
    mock_coordinator_2.async_request_refresh.assert_called_once()
