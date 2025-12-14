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
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name="SNCB/NMBS",
            manufacturer="SNCB/NMBS",
            entry_type=DeviceEntryType.SERVICE,
        )
