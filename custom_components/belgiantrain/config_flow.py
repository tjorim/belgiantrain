"""Config flow for the SNCB/NMBS integration."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentry,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from pyrail import iRail

from .const import (
    CONF_EXCLUDE_VIAS,
    CONF_SHOW_ON_MAP,
    CONF_STATION_FROM,
    CONF_STATION_LIVE,
    CONF_STATION_TO,
    DOMAIN,
    SUBENTRY_TYPE_CONNECTION,
    SUBENTRY_TYPE_LIVEBOARD,
)

if TYPE_CHECKING:
    from pyrail.models import StationDetails


class NMBSConfigFlow(ConfigFlow, domain=DOMAIN):
    """NMBS config flow."""

    def __init__(self) -> None:
        """Initialize."""
        self.stations: list[StationDetails] = []

    async def _fetch_stations(self) -> list[StationDetails]:
        """Fetch the stations."""
        api_client = iRail(session=async_get_clientsession(self.hass))
        stations_response = await api_client.get_stations()
        if stations_response is None:
            msg = "The API is currently unavailable."
            raise CannotConnectError(msg)
        return stations_response.stations

    async def _fetch_stations_choices(self) -> list[SelectOptionDict]:
        """Fetch the stations options."""
        if len(self.stations) == 0:
            self.stations = await self._fetch_stations()

        return [
            SelectOptionDict(value=station.id, label=station.standard_name)
            for station in self.stations
        ]

    async def async_step_user(
        self, _user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial setup of the integration."""
        # Check if already configured
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        # Verify API is available by fetching stations
        try:
            await self._fetch_stations()
        except CannotConnectError:
            return self.async_abort(reason="api_unavailable")

        # Show menu to choose first sensor type
        return self.async_show_menu(
            step_id="user",
            menu_options=["connection", "liveboard"],
        )

    async def async_step_connection(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle adding a connection during initial setup."""
        if user_input is not None and not hasattr(self, "connection_data"):
            # Validate that departure and arrival stations are different
            if user_input[CONF_STATION_FROM] == user_input[CONF_STATION_TO]:
                errors = {"base": "same_station"}
            else:
                # Store connection data and move to liveboard options
                self.connection_data = user_input
                return await self.async_step_connection_liveboards()
        else:
            errors = {}

        # Fetch station choices
        try:
            choices = await self._fetch_stations_choices()
        except CannotConnectError:
            return self.async_abort(reason="api_unavailable")

        schema = vol.Schema(
            {
                vol.Required(CONF_STATION_FROM): SelectSelector(
                    SelectSelectorConfig(
                        options=choices,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_STATION_TO): SelectSelector(
                    SelectSelectorConfig(
                        options=choices,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_EXCLUDE_VIAS): BooleanSelector(),
                vol.Optional(CONF_SHOW_ON_MAP): BooleanSelector(),
            }
        )

        return self.async_show_form(
            step_id="connection",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_connection_liveboards(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask if user wants to add liveboards for departure/arrival stations."""
        if user_input is not None:
            # Create main entry with connection and optional liveboards
            data = {"first_connection": self.connection_data}

            liveboards_to_add = []
            if user_input.get("add_departure_liveboard", False):
                liveboards_to_add.append(self.connection_data[CONF_STATION_FROM])
            if user_input.get("add_arrival_liveboard", False):
                liveboards_to_add.append(self.connection_data[CONF_STATION_TO])

            if liveboards_to_add:
                data["liveboards_to_add"] = liveboards_to_add

            return self.async_create_entry(
                title="SNCB/NMBS Belgian Trains",
                data=data,
            )

        # Get station names for the checkboxes
        from_id = self.connection_data[CONF_STATION_FROM]
        to_id = self.connection_data[CONF_STATION_TO]
        station_from = next((s for s in self.stations if s.id == from_id), None)
        station_to = next((s for s in self.stations if s.id == to_id), None)

        if not station_from or not station_to:
            # Fallback if stations not found
            return self.async_create_entry(
                title="SNCB/NMBS Belgian Trains",
                data={"first_connection": self.connection_data},
            )

        schema = vol.Schema(
            {
                vol.Optional(
                    "add_departure_liveboard", default=False
                ): BooleanSelector(),
                vol.Optional("add_arrival_liveboard", default=False): BooleanSelector(),
            }
        )

        return self.async_show_form(
            step_id="connection_liveboards",
            data_schema=schema,
            description_placeholders={
                "departure_station": station_from.standard_name,
                "arrival_station": station_to.standard_name,
            },
        )

    async def async_step_liveboard(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle adding a liveboard during initial setup."""
        if user_input is not None:
            # Create main entry and store liveboard data to be added as subentry
            return self.async_create_entry(
                title="SNCB/NMBS Belgian Trains",
                data={"first_liveboard": user_input},
            )

        # Fetch station choices
        try:
            choices = await self._fetch_stations_choices()
        except CannotConnectError:
            return self.async_abort(reason="api_unavailable")

        errors: dict = {}
        schema = vol.Schema(
            {
                vol.Required(CONF_STATION_LIVE): SelectSelector(
                    SelectSelectorConfig(
                        options=choices,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="liveboard",
            data_schema=schema,
            errors=errors,
        )


class ConnectionFlowHandler(ConfigSubentryFlow):
    """Handle subentry flow for connection sensors."""

    def __init__(self) -> None:
        """Initialize."""
        self.connection_data: dict[str, Any] = {}
        self.stations: list[StationDetails] = []
        self.station_from: StationDetails | None = None
        self.station_to: StationDetails | None = None

    def _create_liveboard_if_needed(
        self,
        main_entry: ConfigEntry,
        station_id: str,
        station_name: str,
    ) -> None:
        """Create a liveboard subentry if it doesn't already exist."""
        liveboard_unique_id = f"liveboard_{station_id}"

        # Check if liveboard already exists
        liveboard_exists = any(
            sub.unique_id == liveboard_unique_id
            for sub in main_entry.subentries.values()
        )

        if not liveboard_exists:
            liveboard_data = {CONF_STATION_LIVE: station_id}
            liveboard_subentry = ConfigSubentry(
                data=MappingProxyType(liveboard_data),
                unique_id=liveboard_unique_id,
                subentry_type=SUBENTRY_TYPE_LIVEBOARD,
                title=f"Liveboard - {station_name}",
            )
            self.hass.config_entries.async_add_subentry(
                main_entry, liveboard_subentry
            )

    async def async_step_user(  # noqa: PLR0911
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Handle the step to setup a connection between 2 stations."""
        errors: dict = {}

        if user_input is not None and not self.connection_data:
            if user_input[CONF_STATION_FROM] == user_input[CONF_STATION_TO]:
                errors["base"] = "same_station"
            else:
                # Fetch stations for validation
                try:
                    api_client = iRail(
                        session=async_get_clientsession(self.hass)
                    )
                    stations_response = await api_client.get_stations()
                    if stations_response is None:
                        return self.async_abort(reason="api_unavailable")
                    self.stations = stations_response.stations
                except CannotConnectError:
                    return self.async_abort(reason="api_unavailable")

                station_from_id = user_input[CONF_STATION_FROM]
                station_to_id = user_input[CONF_STATION_TO]
                self.station_from = next(
                    (s for s in self.stations if s.id == station_from_id),
                    None,
                )
                self.station_to = next(
                    (s for s in self.stations if s.id == station_to_id),
                    None,
                )

                if self.station_from is None or self.station_to is None:
                    errors["base"] = "invalid_station"
                else:
                    # Check if this connection already exists
                    excl_vias = user_input.get(CONF_EXCLUDE_VIAS)
                    vias = "_excl_vias" if excl_vias else ""
                    unique_id = (
                        f"connection_{station_from_id}_{station_to_id}{vias}"
                    )
                    for entry in self.hass.config_entries.async_entries(DOMAIN):
                        for subentry in entry.subentries.values():
                            if subentry.unique_id == unique_id:
                                return self.async_abort(
                                    reason="already_configured"
                                )

                    # Store connection data and move to liveboard options
                    self.connection_data = user_input
                    return await self.async_step_liveboards()

        # Fetch station choices
        try:
            api_client = iRail(session=async_get_clientsession(self.hass))
            stations_response = await api_client.get_stations()
            if stations_response is None:
                return self.async_abort(reason="api_unavailable")

            choices = [
                SelectOptionDict(value=station.id, label=station.standard_name)
                for station in stations_response.stations
            ]
        except CannotConnectError:
            return self.async_abort(reason="api_unavailable")

        schema = vol.Schema(
            {
                vol.Required(CONF_STATION_FROM): SelectSelector(
                    SelectSelectorConfig(
                        options=choices,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_STATION_TO): SelectSelector(
                    SelectSelectorConfig(
                        options=choices,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_EXCLUDE_VIAS): BooleanSelector(),
                vol.Optional(CONF_SHOW_ON_MAP): BooleanSelector(),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

        async def async_step_liveboards(
            self, user_input: dict[str, Any] | None = None
        ) -> SubentryFlowResult:
            """Ask if user wants to add liveboards for stations."""
            # Add null checks for safety
            if self.station_from is None or self.station_to is None:
                return self.async_abort(reason="invalid_state")

            if user_input is not None:
                # Create the connection subentry
                excl_vias = self.connection_data.get(CONF_EXCLUDE_VIAS)
                vias = "_excl_vias" if excl_vias else ""
                station_from_id = self.connection_data[CONF_STATION_FROM]
                station_to_id = self.connection_data[CONF_STATION_TO]
                unique_id = f"connection_{station_from_id}_{station_to_id}{vias}"

                # Get parent entry directly from context (more efficient)
                main_entry = self.hass.config_entries.async_get_entry(
                    self.context["parent_entry_id"]
                )

                # Create liveboard subentries if requested
                if main_entry is not None:
                    if user_input.get("add_departure_liveboard", False):
                        self._create_liveboard_if_needed(
                            main_entry,
                            station_from_id,
                            self.station_from.standard_name,
                        )

                    if user_input.get("add_arrival_liveboard", False):
                        self._create_liveboard_if_needed(
                            main_entry,
                            station_to_id,
                            self.station_to.standard_name,
                        )

                # Create the connection subentry
                return self.async_create_entry(
                    title=(
                        f"Connection: {self.station_from.standard_name} → "
                        f"{self.station_to.standard_name}"
                    ),
                    data=self.connection_data,
                    unique_id=unique_id,
                )

            # Show form with checkboxes for liveboards
            schema = vol.Schema(
                {
                    vol.Optional(
                        "add_departure_liveboard", default=False
                    ): BooleanSelector(),
                    vol.Optional(
                        "add_arrival_liveboard", default=False
                    ): BooleanSelector(),
                }
            )

            return self.async_show_form(
                step_id="liveboards",
                data_schema=schema,
                description_placeholders={
                    "departure_station": self.station_from.standard_name,
                    "arrival_station": self.station_to.standard_name,
                },
            )

class LiveboardFlowHandler(ConfigSubentryFlow):
    """Handle subentry flow for liveboard sensors."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Handle the step to setup a liveboard sensor for a station."""
        errors: dict = {}

        # Fetch stations if not already done
        if user_input is not None:
            station_id = user_input[CONF_STATION_LIVE]

            # Check if this station is already configured as a subentry
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                for subentry in entry.subentries.values():
                    if subentry.unique_id == f"liveboard_{station_id}":
                        return self.async_abort(reason="already_configured")

            # Get station details for the title
            stations = self.hass.data.get(DOMAIN, {}).get("stations", [])
            station = next((s for s in stations if s.id == station_id), None)

            if station is None:
                errors["base"] = "invalid_station"
            else:
                return self.async_create_entry(
                    title=f"Liveboard - {station.standard_name}",
                    data={CONF_STATION_LIVE: station_id},
                    unique_id=f"liveboard_{station_id}",
                )

        # Fetch station choices
        try:
            api_client = iRail(session=async_get_clientsession(self.hass))
            stations_response = await api_client.get_stations()
            if stations_response is None:
                return self.async_abort(reason="api_unavailable")

            choices = [
                SelectOptionDict(value=station.id, label=station.standard_name)
                for station in stations_response.stations
            ]
        except CannotConnectError:
            return self.async_abort(reason="api_unavailable")

        schema = vol.Schema(
            {
                vol.Required(CONF_STATION_LIVE): SelectSelector(
                    SelectSelectorConfig(
                        options=choices,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

# Add the method to the class after both handlers are defined
@classmethod
@callback
def _async_get_supported_subentry_types(
    _cls: type[NMBSConfigFlow], _config_entry: ConfigEntry
) -> dict[str, type[ConfigSubentryFlow]]:
    """Return subentries supported by this handler."""
    return {
        SUBENTRY_TYPE_CONNECTION: ConnectionFlowHandler,
        SUBENTRY_TYPE_LIVEBOARD: LiveboardFlowHandler,
    }

# Dynamically add the method to NMBSConfigFlow
NMBSConfigFlow.async_get_supported_subentry_types = (
    _async_get_supported_subentry_types  # type: ignore[method-assign]
)


class CannotConnectError(Exception):
    """Error to indicate we cannot connect to NMBS."""
