"""Common fixtures for the SNCB/NMBS tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.core import HomeAssistant


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""
    yield


@pytest.fixture
async def hass_with_station_data(hass: HomeAssistant):
    """Provide a hass instance with station data preloaded."""
    # Mock the station data in hass.data
    from unittest.mock import MagicMock

    mock_station_1 = MagicMock()
    mock_station_1.id = "BE.NMBS.008812005"
    mock_station_1.standard_name = "Brussels-Central"
    mock_station_1.name = "Brussels-Central"

    mock_station_2 = MagicMock()
    mock_station_2.id = "BE.NMBS.008892007"
    mock_station_2.standard_name = "Ghent-Sint-Pieters"
    mock_station_2.name = "Ghent-Sint-Pieters"

    hass.data.setdefault("belgiantrain", [mock_station_1, mock_station_2])
    return hass


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup and async_setup_entry."""
    with (
        patch("custom_components.belgiantrain.async_setup", return_value=True),
        patch(
            "custom_components.belgiantrain.async_setup_entry", return_value=True
        ) as mock_setup_entry,
    ):
        yield mock_setup_entry
