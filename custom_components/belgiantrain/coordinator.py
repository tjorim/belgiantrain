"""DataUpdateCoordinator for belgiantrain."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pyrail import iRail
    from pyrail.models import StationDetails

_LOGGER = logging.getLogger(__name__)


class BelgianTrainDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Belgian train data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_client: iRail,
        station_from: StationDetails,
        station_to: StationDetails,
    ) -> None:
        """Initialize the coordinator."""
        self.api_client = api_client
        self.station_from = station_from
        self.station_to = station_to

        super().__init__(
            hass,
            _LOGGER,
            name="Belgian Train",
            update_interval=timedelta(minutes=1),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            # Fetch connection data
            connections = await self.api_client.get_connections(
                self.station_from.id, self.station_to.id
            )

            # Fetch liveboard data for both stations
            liveboard_from = await self.api_client.get_liveboard(self.station_from.id)
            liveboard_to = await self.api_client.get_liveboard(self.station_to.id)

            if connections is None:
                msg = "Failed to fetch train connections from iRail API"
                raise UpdateFailed(msg)

            if liveboard_from is None or liveboard_to is None:
                msg = "Failed to fetch liveboard data from iRail API"
                raise UpdateFailed(msg)

            return {
                "connections": connections,
                "liveboard_from": liveboard_from,
                "liveboard_to": liveboard_to,
            }
        except Exception as err:
            msg = f"Error communicating with iRail API: {err}"
            raise UpdateFailed(msg) from err
