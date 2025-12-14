"""Custom types for belgiantrain."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .coordinator import (
        BelgianTrainDataUpdateCoordinator,
        LiveboardDataUpdateCoordinator,
    )


# Type alias for config entries with runtime_data.
# Available for future use when legacy backward compatibility is no longer needed.
# Aligns with Home Assistant integration blueprint patterns.
type BelgianTrainConfigEntry = ConfigEntry[BelgianTrainData]


@dataclass
class BelgianTrainData:
    """Data for the Belgian Train integration."""

    # Stores either a connection or liveboard coordinator instance for the config entry
    coordinator: BelgianTrainDataUpdateCoordinator | LiveboardDataUpdateCoordinator
