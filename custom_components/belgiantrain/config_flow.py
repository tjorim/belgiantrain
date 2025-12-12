"""Config flow for the SNCB/NMBS integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
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
    SUBENTRY_TYPE_LIVEBOARD,
)

if TYPE_CHECKING:
    from pyrail.models import StationDetails


class NMBSConfigFlow(ConfigFlow, domain=DOMAIN):
    """NMBS config flow."""

    def __init__(self) -> None:
        """Initialize."""
        self.stations: list[StationDetails] = []

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, _config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentries supported by this handler."""
        return {SUBENTRY_TYPE_LIVEBOARD: LiveboardFlowHandler}

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
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the step to setup a connection between 2 stations."""
        try:
            choices = await self._fetch_stations_choices()
        except CannotConnectError:
            return self.async_abort(reason="api_unavailable")

        errors: dict = {}
        if user_input is not None:
            if user_input[CONF_STATION_FROM] == user_input[CONF_STATION_TO]:
                errors["base"] = "same_station"
            else:
                station_from = next(
                    (
                        station
                        for station in self.stations
                        if station.id == user_input[CONF_STATION_FROM]
                    ),
                    None,
                )
                station_to = next(
                    (
                        station
                        for station in self.stations
                        if station.id == user_input[CONF_STATION_TO]
                    ),
                    None,
                )

                if station_from is None or station_to is None:
                    errors["base"] = "invalid_station"
                else:
                    vias = "_excl_vias" if user_input.get(CONF_EXCLUDE_VIAS) else ""
                    await self.async_set_unique_id(
                        f"{user_input[CONF_STATION_FROM]}_{user_input[CONF_STATION_TO]}{vias}"
                    )
                    self._abort_if_unique_id_configured()

                    config_entry_name = (
                        f"Train from {station_from.standard_name} "
                        f"to {station_to.standard_name}"
                    )
                    return self.async_create_entry(
                        title=config_entry_name,
                        data=user_input,
                    )

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
            },
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


class CannotConnectError(Exception):
    """Error to indicate we cannot connect to NMBS."""
