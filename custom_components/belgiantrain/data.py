"""Custom types for belgiantrain."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from . import BelgiantrainApiClient
    from .coordinator import BelgiantrainDataUpdateCoordinator


# TODO Create ConfigEntry type alias with API object
# TODO Rename type alias and update all entry annotations
type BelgiantrainConfigEntry = ConfigEntry[BelgiantrainData]


@dataclass
class BelgiantrainData:
    """Data for the belgiantrain integration."""

    client: BelgiantrainApiClient
    coordinator: BelgiantrainDataUpdateCoordinator
    integration: Integration
