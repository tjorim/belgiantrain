"""BelgianTrainEntity class."""

from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

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

    Provides standardized entity naming.
    Available for future use when refactoring existing sensor entities.
    Aligns with Home Assistant integration blueprint patterns.
    """

    _attr_has_entity_name = True
