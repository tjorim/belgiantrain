"""Repairs for the SNCB/NMBS integration."""

from __future__ import annotations

import logging
from types import MappingProxyType
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components.repairs import RepairsFlow
from homeassistant.config_entries import ConfigSubentry

from .const import (
    CONF_EXCLUDE_VIAS,
    CONF_SHOW_ON_MAP,
    CONF_STATION_FROM,
    CONF_STATION_TO,
    DOMAIN,
    SUBENTRY_TYPE_CONNECTION,
    find_station,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.data_entry_flow import FlowResult

_LOGGER = logging.getLogger(__name__)


class MigrateLegacyConnectionRepairFlow(RepairsFlow):
    """Handler for migrating legacy connection entries."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize the repair flow."""
        super().__init__()
        self._hass = hass
        self._entry_id = entry_id

    async def async_step_init(
        self, _user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Confirm migration of legacy connection entry."""
        if user_input is not None:
            # Perform the migration
            success = await self._migrate_legacy_entry()
            if success:
                return self.async_create_entry(title="", data={})
            # If migration failed, show error form
            return self.async_show_form(
                step_id="confirm",
                data_schema=vol.Schema({}),
                description_placeholders={},
                errors={"base": "migration_failed"},
            )

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={},
        )

    async def _migrate_legacy_entry(self) -> bool:  # noqa: PLR0911
        """Migrate a legacy connection entry to new subentry format.

        Returns True if migration was successful.
        """
        # Get the legacy entry
        legacy_entry = self._hass.config_entries.async_get_entry(self._entry_id)
        if legacy_entry is None:
            _LOGGER.error("Legacy entry %s not found", self._entry_id)
            return False

        # Validate that this is actually a legacy entry
        if not (
            CONF_STATION_FROM in legacy_entry.data
            and CONF_STATION_TO in legacy_entry.data
        ):
            _LOGGER.error(
                "Entry %s is not a legacy connection entry", self._entry_id
            )
            return False

        # Get station IDs from legacy entry
        station_from_id = legacy_entry.data[CONF_STATION_FROM]
        station_to_id = legacy_entry.data[CONF_STATION_TO]
        exclude_vias = legacy_entry.data.get(CONF_EXCLUDE_VIAS, False)
        show_on_map = legacy_entry.data.get(CONF_SHOW_ON_MAP, False)

        # Validate stations exist
        station_from = find_station(self._hass, station_from_id)
        station_to = find_station(self._hass, station_to_id)

        if station_from is None or station_to is None:
            _LOGGER.error(
                "Cannot migrate entry %s: invalid stations (from=%s, to=%s)",
                self._entry_id,
                station_from_id,
                station_to_id,
            )
            return False

        _LOGGER.info(
            "Migrating legacy connection entry: %s → %s",
            station_from.standard_name,
            station_to.standard_name,
        )

        # Check if a main entry already exists
        main_entry = None
        for entry in self._hass.config_entries.async_entries(DOMAIN):
            if (
                entry.unique_id == DOMAIN
                and not getattr(entry, "subentry_type", None)
                and CONF_STATION_FROM not in entry.data
            ):
                main_entry = entry
                break

        # Create main entry if it doesn't exist
        if main_entry is None:
            _LOGGER.debug("Creating new main entry for migration")
            result = await self._hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "repairs"},
                data={},
            )
            if result["type"] != "create_entry":
                _LOGGER.error("Failed to create main entry during migration")
                return False
            # Get the newly created main entry
            main_entry = self._hass.config_entries.async_get_entry(
                result["result"].entry_id
            )
            if main_entry is None:
                _LOGGER.error("Could not retrieve newly created main entry")
                return False

        # Create connection data for subentry
        vias = "_excl_vias" if exclude_vias else ""
        conn_id = f"{station_from_id}_{station_to_id}"
        unique_id = f"belgiantrain_connection_{conn_id}{vias}"

        # Check if this connection already exists as a subentry
        subentry_exists = any(
            sub.unique_id == unique_id
            for sub in getattr(main_entry, "subentries", {}).values()
        )
        if subentry_exists:
            _LOGGER.info("Connection subentry already exists, removing legacy entry")
            # Just remove the legacy entry since the connection is already configured
            await self._hass.config_entries.async_remove(self._entry_id)
            return True

        # Create the connection subentry
        connection_data = {
            CONF_STATION_FROM: station_from_id,
            CONF_STATION_TO: station_to_id,
            CONF_EXCLUDE_VIAS: exclude_vias,
            CONF_SHOW_ON_MAP: show_on_map,
        }

        subentry_title = (
            f"Connection: {station_from.standard_name} → "
            f"{station_to.standard_name}"
        )
        subentry = ConfigSubentry(
            data=MappingProxyType(connection_data),
            unique_id=unique_id,
            subentry_type=SUBENTRY_TYPE_CONNECTION,
            title=subentry_title,
        )

        _LOGGER.debug(
            "Creating connection subentry from migration: %s → %s",
            station_from.standard_name,
            station_to.standard_name,
        )
        self._hass.config_entries.async_add_subentry(main_entry, subentry)

        # Remove the legacy entry
        _LOGGER.info("Migration complete, removing legacy entry %s", self._entry_id)
        await self._hass.config_entries.async_remove(self._entry_id)

        return True


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    _data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create flow for repair."""
    if issue_id.startswith("migrate_legacy_connection_"):
        entry_id = issue_id.replace("migrate_legacy_connection_", "")
        return MigrateLegacyConnectionRepairFlow(hass, entry_id)
    # Unknown repair issue
    msg = f"Unknown repair issue: {issue_id}"
    raise ValueError(msg)
