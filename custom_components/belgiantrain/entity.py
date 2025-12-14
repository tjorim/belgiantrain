"""BelgianTrainEntity class."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import (
    BelgianTrainDataUpdateCoordinator,
    LiveboardDataUpdateCoordinator,
)


class BelgianTrainEntity(
    CoordinatorEntity[
        BelgianTrainDataUpdateCoordinator | LiveboardDataUpdateCoordinator
    ]
):
    """Base entity for Belgian Train integration.

    Provides standardized device info and entity naming.
    Available for future use when refactoring existing sensor entities.
    Aligns with Home Assistant integration blueprint patterns.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BelgianTrainDataUpdateCoordinator | LiveboardDataUpdateCoordinator,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)

        # For subentries, use parent entry's ID to group entities
        # For main entry or legacy entries, use the entry's own ID
        entry = coordinator.config_entry
        device_entry_id = entry.entry_id

        # Check if this is a subentry (has a parent)
        if hasattr(entry, "parent_entry") and entry.parent_entry is not None:
            device_entry_id = entry.parent_entry.entry_id

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_entry_id)},
            name="SNCB/NMBS",
            manufacturer="SNCB/NMBS",
            entry_type=DeviceEntryType.SERVICE,
        )
