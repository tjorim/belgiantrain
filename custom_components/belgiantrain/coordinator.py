"""DataUpdateCoordinator for belgiantrain."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from . import (
    BelgiantrainApiClientAuthenticationError,
    BelgiantrainApiClientError,
)

if TYPE_CHECKING:
    from . import BelgiantrainConfigEntry


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class BelgiantrainDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: BelgiantrainConfigEntry

    async def _async_update_data(self) -> Any:
        """Update data via library."""
        try:
            return await self.config_entry.runtime_data.client.async_get_data()
        except BelgiantrainApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except BelgiantrainApiClientError as exception:
            raise UpdateFailed(exception) from exception
