"""Config flow for the SNCB/NMBS integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

# ConfigSubentryFlow is only available in Home Assistant 2025.2+
try:
    from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
except ImportError:
    # Fallback for older versions - this won't be used but prevents import errors
    ConfigSubentryFlow = None  # type: ignore[misc,assignment]
    SubentryFlowResult = None  # type: ignore[misc,assignment]
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

        # Create the main integration entry (no specific data)
        return self.async_create_entry(
            title="SNCB/NMBS Belgian Trains",
            data={},
        )


if ConfigSubentryFlow is not None:

    class ConnectionFlowHandler(ConfigSubentryFlow):
        """Handle subentry flow for connection sensors."""

        async def async_step_user(  # noqa: PLR0911
            self, user_input: dict[str, Any] | None = None
        ) -> SubentryFlowResult:
            """Handle the step to setup a connection between 2 stations."""
            errors: dict = {}

            if user_input is not None:
                if user_input[CONF_STATION_FROM] == user_input[CONF_STATION_TO]:
                    errors["base"] = "same_station"
                else:
                    # Fetch stations for validation
                    try:
                        api_client = iRail(session=async_get_clientsession(self.hass))
                        stations_response = await api_client.get_stations()
                        if stations_response is None:
                            return self.async_abort(reason="api_unavailable")
                        stations = stations_response.stations
                    except CannotConnectError:
                        return self.async_abort(reason="api_unavailable")

                    station_from = next(
                        (s for s in stations if s.id == user_input[CONF_STATION_FROM]),
                        None,
                    )
                    station_to = next(
                        (s for s in stations if s.id == user_input[CONF_STATION_TO]),
                        None,
                    )

                    if station_from is None or station_to is None:
                        errors["base"] = "invalid_station"
                    else:
                        # Check if this connection already exists as a subentry
                        vias = "_excl_vias" if user_input.get(CONF_EXCLUDE_VIAS) else ""
                        unique_id = (
                            f"connection_{user_input[CONF_STATION_FROM]}_"
                            f"{user_input[CONF_STATION_TO]}{vias}"
                        )
                        for entry in self.hass.config_entries.async_entries(DOMAIN):
                            for subentry in entry.subentries.values():
                                if subentry.unique_id == unique_id:
                                    return self.async_abort(
                                        reason="already_configured"
                                    )

                        return self.async_create_entry(
                            title=(
                                f"Connection: {station_from.standard_name} → "
                                f"{station_to.standard_name}"
                            ),
                            data=user_input,
                            unique_id=unique_id,
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

else:
    # Fallback classes when ConfigSubentryFlow is not available
    ConnectionFlowHandler = None  # type: ignore[assignment,misc]
    LiveboardFlowHandler = None  # type: ignore[assignment,misc]


class CannotConnectError(Exception):
    """Error to indicate we cannot connect to NMBS."""
