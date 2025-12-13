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


type BelgianTrainConfigEntry = ConfigEntry[BelgianTrainData]


@dataclass
class BelgianTrainData:
    """Data for the Belgian Train integration."""

    coordinator: BelgianTrainDataUpdateCoordinator | LiveboardDataUpdateCoordinator
