"""Diagnostics support for Belgian Train integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    diagnostics_data: dict[str, Any] = {
        "entry": {
            "entry_id": entry.entry_id,
            "version": entry.version,
            "minor_version": entry.minor_version,
            "domain": entry.domain,
            "title": entry.title,
            "data": dict(entry.data),
            "options": dict(entry.options),
            "unique_id": entry.unique_id,
            "disabled_by": entry.disabled_by,
            "state": entry.state.value if entry.state else None,
        },
        "subentries": {},
        "coordinators": {},
    }

    # Add subentry information
    if hasattr(entry, "subentries"):
        for subentry_id, subentry in entry.subentries.items():
            subentry_type = getattr(subentry, "subentry_type", None)
            subentry_state = getattr(subentry, "state", None)
            diagnostics_data["subentries"][subentry_id] = {
                "unique_id": subentry.unique_id,
                "subentry_type": subentry_type,
                "title": subentry.title,
                "data": dict(subentry.data),
                "disabled_by": getattr(subentry, "disabled_by", None),
                "state": subentry_state.value if subentry_state else None,
            }

    # Add coordinator information
    domain_data = hass.data.get(DOMAIN, {})
    coordinators = domain_data.get("coordinators", {})

    for coord_id, coordinator in coordinators.items():
        coord_data: dict[str, Any] = {
            "entry_id": coord_id,
            "last_update_success": coordinator.last_update_success,
        }

        # Add last exception info if available
        if coordinator.last_exception:
            coord_data["last_exception"] = str(coordinator.last_exception)

        # Add coordinator data if available
        if coordinator.data:
            coord_data["data_available"] = True
            coord_data["data_type"] = type(coordinator.data).__name__

        diagnostics_data["coordinators"][coord_id] = coord_data

    # Add station data
    stations = domain_data.get("stations", [])
    diagnostics_data["stations_count"] = len(stations)

    return diagnostics_data
