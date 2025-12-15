"""Test the SNCB/NMBS repairs."""

# ruff: noqa: SLF001, PT019

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from custom_components.belgiantrain import async_setup_entry
from custom_components.belgiantrain.const import (
    CONF_EXCLUDE_VIAS,
    CONF_SHOW_ON_MAP,
    CONF_STATION_FROM,
    CONF_STATION_TO,
    DOMAIN,
)
from custom_components.belgiantrain.repairs import (
    MigrateLegacyConnectionRepairFlow,
    async_create_fix_flow,
)


@pytest.fixture
def mock_stations(hass: HomeAssistant) -> None:
    """Mock station data for tests."""
    mock_station_1 = MagicMock()
    mock_station_1.id = "BE.NMBS.008812005"
    mock_station_1.standard_name = "Brussels-Central"
    mock_station_1.name = "Brussels-Central"

    mock_station_2 = MagicMock()
    mock_station_2.id = "BE.NMBS.008892007"
    mock_station_2.standard_name = "Ghent-Sint-Pieters"
    mock_station_2.name = "Ghent-Sint-Pieters"

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["stations"] = [mock_station_1, mock_station_2]


async def test_async_create_fix_flow(hass: HomeAssistant) -> None:
    """Test that async_create_fix_flow creates the correct repair flow."""
    entry_id = "test_entry_123"
    issue_id = f"migrate_legacy_connection_{entry_id}"

    flow = await async_create_fix_flow(hass, issue_id, None)

    assert isinstance(flow, MigrateLegacyConnectionRepairFlow)


async def test_async_create_fix_flow_unknown_issue(hass: HomeAssistant) -> None:
    """Test that async_create_fix_flow raises error for unknown issue."""
    with pytest.raises(ValueError, match="Unknown repair issue"):
        await async_create_fix_flow(hass, "unknown_issue", None)


async def test_migrate_legacy_entry_success(
    hass: HomeAssistant, _mock_stations: None
) -> None:
    """Test successful migration of a legacy connection entry."""
    # Create a legacy config entry
    legacy_entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Brussels → Ghent",
        data={
            CONF_STATION_FROM: "BE.NMBS.008812005",
            CONF_STATION_TO: "BE.NMBS.008892007",
            CONF_EXCLUDE_VIAS: False,
            CONF_SHOW_ON_MAP: False,
        },
        source="user",
    )

    # Mock config entries
    hass.config_entries._entries[legacy_entry.entry_id] = legacy_entry

    # Create a main entry to migrate to
    main_entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="SNCB/NMBS",
        data={},
        source="user",
        unique_id=DOMAIN,
    )
    hass.config_entries._entries[main_entry.entry_id] = main_entry

    # Create the repair flow
    flow = MigrateLegacyConnectionRepairFlow(hass, legacy_entry.entry_id)

    # Mock async_add_subentry and async_remove
    with (
        patch.object(
            hass.config_entries, "async_add_subentry"
        ) as mock_add_subentry,
        patch.object(
            hass.config_entries, "async_remove", return_value=None
        ) as mock_remove,
    ):
        result = await flow._migrate_legacy_entry()

    assert result is True
    mock_add_subentry.assert_called_once()
    mock_remove.assert_called_once_with(legacy_entry.entry_id)


async def test_migrate_legacy_entry_already_exists(
    hass: HomeAssistant, _mock_stations: None
) -> None:
    """Test migration when connection already exists as subentry."""
    # Create a legacy config entry
    legacy_entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Brussels → Ghent",
        data={
            CONF_STATION_FROM: "BE.NMBS.008812005",
            CONF_STATION_TO: "BE.NMBS.008892007",
            CONF_EXCLUDE_VIAS: False,
            CONF_SHOW_ON_MAP: False,
        },
        source="user",
    )
    hass.config_entries._entries[legacy_entry.entry_id] = legacy_entry

    # Create main entry with existing subentry
    main_entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="SNCB/NMBS",
        data={},
        source="user",
        unique_id=DOMAIN,
    )
    hass.config_entries._entries[main_entry.entry_id] = main_entry

    # Mock subentries to include the connection
    unique_id = (
        "belgiantrain_connection_BE.NMBS.008812005_BE.NMBS.008892007"
    )
    mock_subentry = MagicMock()
    mock_subentry.unique_id = unique_id
    main_entry.subentries = {mock_subentry.unique_id: mock_subentry}

    # Create the repair flow
    flow = MigrateLegacyConnectionRepairFlow(hass, legacy_entry.entry_id)

    # Mock async_remove
    with patch.object(
        hass.config_entries, "async_remove", return_value=None
    ) as mock_remove:
        result = await flow._migrate_legacy_entry()

    assert result is True
    mock_remove.assert_called_once_with(legacy_entry.entry_id)


async def test_migrate_legacy_entry_invalid_stations(
    hass: HomeAssistant, _mock_stations: None
) -> None:
    """Test migration fails with invalid station data."""
    # Create a legacy entry with invalid station IDs
    legacy_entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Invalid → Connection",
        data={
            CONF_STATION_FROM: "INVALID_ID_1",
            CONF_STATION_TO: "INVALID_ID_2",
        },
        source="user",
    )
    hass.config_entries._entries[legacy_entry.entry_id] = legacy_entry

    # Create the repair flow
    flow = MigrateLegacyConnectionRepairFlow(hass, legacy_entry.entry_id)
    result = await flow._migrate_legacy_entry()

    assert result is False


async def test_migrate_legacy_entry_not_found(hass: HomeAssistant) -> None:
    """Test migration fails when legacy entry not found."""
    flow = MigrateLegacyConnectionRepairFlow(hass, "nonexistent_entry_id")
    result = await flow._migrate_legacy_entry()

    assert result is False


async def test_repair_flow_confirm_step(
    hass: HomeAssistant, _mock_stations: None
) -> None:
    """Test the confirm step of the repair flow."""
    # Create a legacy config entry
    legacy_entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Brussels → Ghent",
        data={
            CONF_STATION_FROM: "BE.NMBS.008812005",
            CONF_STATION_TO: "BE.NMBS.008892007",
        },
        source="user",
    )
    hass.config_entries._entries[legacy_entry.entry_id] = legacy_entry

    # Create a main entry
    main_entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="SNCB/NMBS",
        data={},
        source="user",
        unique_id=DOMAIN,
    )
    hass.config_entries._entries[main_entry.entry_id] = main_entry

    # Create the repair flow
    flow = MigrateLegacyConnectionRepairFlow(hass, legacy_entry.entry_id)

    # Test showing the form
    result = await flow.async_step_confirm()
    assert result["type"] == "form"
    assert result["step_id"] == "confirm"

    # Test submitting the form
    with (
        patch.object(
            hass.config_entries, "async_add_subentry"
        ),
        patch.object(
            hass.config_entries, "async_remove", return_value=None
        ),
    ):
        result = await flow.async_step_confirm(user_input={})

    assert result["type"] == "create_entry"


async def test_repair_flow_confirm_step_failure(
    hass: HomeAssistant, _mock_stations: None
) -> None:
    """Test the confirm step when migration fails."""
    # Create a legacy entry with invalid data
    legacy_entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Invalid",
        data={
            CONF_STATION_FROM: "INVALID_ID",
            CONF_STATION_TO: "ALSO_INVALID",
        },
        source="user",
    )
    hass.config_entries._entries[legacy_entry.entry_id] = legacy_entry

    # Create the repair flow
    flow = MigrateLegacyConnectionRepairFlow(hass, legacy_entry.entry_id)

    # Test submitting the form with invalid data
    result = await flow.async_step_confirm(user_input={})

    assert result["type"] == "form"
    assert result["step_id"] == "confirm"
    assert "errors" in result
    assert result["errors"]["base"] == "migration_failed"


async def test_legacy_entry_creates_repair_issue_valid(
    hass: HomeAssistant, _mock_stations: None
) -> None:
    """Test that a valid legacy entry creates a repair issue."""
    # Create a legacy config entry
    legacy_entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Brussels → Ghent",
        data={
            CONF_STATION_FROM: "BE.NMBS.008812005",
            CONF_STATION_TO: "BE.NMBS.008892007",
        },
        source="user",
    )
    hass.config_entries._entries[legacy_entry.entry_id] = legacy_entry

    # Mock the coordinator and API
    with (
        patch(
            "custom_components.belgiantrain.iRail"
        ) as mock_irail,
        patch(
            "custom_components.belgiantrain.BelgianTrainDataUpdateCoordinator"
        ) as mock_coordinator,
    ):
        mock_api = AsyncMock()
        mock_irail.return_value = mock_api

        mock_coord = AsyncMock()
        mock_coord.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator.return_value = mock_coord

        result = await async_setup_entry(hass, legacy_entry)

    assert result is True

    # Check that a repair issue was created
    issue_registry = ir.async_get(hass)
    issue = issue_registry.async_get_issue(
        DOMAIN, f"migrate_legacy_connection_{legacy_entry.entry_id}"
    )
    assert issue is not None
    assert issue.is_fixable is True
    assert issue.severity == ir.IssueSeverity.WARNING


async def test_legacy_entry_creates_repair_issue_invalid(
    hass: HomeAssistant, _mock_stations: None
) -> None:
    """Test that an invalid legacy entry creates a repair issue."""
    # Create a legacy config entry with invalid stations
    legacy_entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Invalid Connection",
        data={
            CONF_STATION_FROM: "INVALID_ID",
            CONF_STATION_TO: "ALSO_INVALID",
        },
        source="user",
    )
    hass.config_entries._entries[legacy_entry.entry_id] = legacy_entry

    result = await async_setup_entry(hass, legacy_entry)

    assert result is False

    # Check that a repair issue was created
    issue_registry = ir.async_get(hass)
    issue = issue_registry.async_get_issue(
        DOMAIN, f"migrate_legacy_connection_{legacy_entry.entry_id}"
    )
    assert issue is not None
    assert issue.is_fixable is True
    assert issue.severity == ir.IssueSeverity.WARNING
