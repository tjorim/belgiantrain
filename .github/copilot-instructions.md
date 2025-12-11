# Copilot Instructions for belgiantrain

This repository contains a Home Assistant custom integration for Belgian trains (SNCB/NMBS) that provides real-time train information via the iRail API.

## Repository Overview

**Purpose**: Home Assistant custom integration for monitoring Belgian train connections and liveboards
**Technology Stack**: Python 3.12+, Home Assistant, pyrail library (iRail API wrapper)
**Data Source**: iRail API (https://api.irail.be/)

## Code Style and Standards

### Linting and Formatting
- **Linter**: Ruff (configuration in `.ruff.toml`)
- **Target Python version**: 3.12+
- Run linting: `scripts/lint` or `ruff check .`
- Code must pass all Ruff checks before committing

### Type Hints
- Use type hints for all function parameters and return values
- Use `TYPE_CHECKING` guards for imports only needed for type annotations
- Example:
  ```python
  from typing import TYPE_CHECKING
  
  if TYPE_CHECKING:
      from homeassistant.config_entries import ConfigEntry
  ```

### Naming Conventions
- Prefix unused function parameters with underscore (e.g., `_config`, `_hass`)
- Exception classes derived from `HomeAssistantError` should end with 'Error' suffix
- Use snake_case for functions and variables
- Use UPPER_CASE for constants in `const.py`

### Import Organization
- Standard library imports first
- Third-party imports second
- Local imports last
- Use absolute imports for local modules (e.g., `from .const import DOMAIN`)

## Integration-Specific Patterns

### Entity Conventions
- Use `entity_registry_enabled_default = False` for sensors that should be disabled by default (e.g., liveboard sensors)
- All entities should have proper unique IDs
- Append `_excl_vias` to unique IDs when the exclude vias option is enabled to allow multiple configurations

### Unique ID Format
- Connection sensors: `{from_station_id}_{to_station_id}` or `{from_station_id}_{to_station_id}_excl_vias`
- Liveboard sensors: `{station_id}_liveboard` or `{station_id}_liveboard_excl_vias`

### Data Flow
1. `__init__.py`: Sets up the integration and fetches station list from iRail API
2. `config_flow.py`: Handles user configuration via UI
3. `sensor.py`: Implements sensor entities for connections and liveboards
4. `const.py`: Contains constants and helper functions

### Station Handling
- Station data is stored in `hass.data[DOMAIN]` as a list of `StationDetails` objects
- Use helper functions from `const.py`:
  - `find_station_by_name()`: Find station by name or standard name
  - `find_station()`: Find station by exact ID

## Development Workflow

### Setup
```bash
scripts/setup  # Install development dependencies
```

### Testing
```bash
pytest tests/belgiantrain/  # Run tests
```

### Linting
```bash
scripts/lint  # Run Ruff linter
```

### Local Development
```bash
scripts/develop  # Start Home Assistant with the integration loaded
```

### Test Structure
- Tests are located in `tests/belgiantrain/`
- Use pytest with async support
- Mock external API calls using fixtures in `conftest.py`
- Test both config flow and sensor functionality

## Key Files

- `custom_components/belgiantrain/__init__.py`: Integration setup and entry point
- `custom_components/belgiantrain/config_flow.py`: Configuration flow UI
- `custom_components/belgiantrain/sensor.py`: Sensor entity implementations
- `custom_components/belgiantrain/const.py`: Constants and helper functions
- `custom_components/belgiantrain/manifest.json`: Integration metadata
- `custom_components/belgiantrain/strings.json`: Translatable strings for UI

## Sensor Types

### Connection Sensors
- Monitor travel time between two stations
- State: Total travel time in minutes
- Attributes: departure info, arrival info, platform numbers, delays, via connections, vehicle ID, cancellation status
- Optionally show map coordinates when `show_on_map` is enabled

### Liveboard Sensors
- Show next departures from a station
- Disabled by default (`entity_registry_enabled_default = False`)
- State: Destination station name
- Attributes: departure time, platform, delay, vehicle ID, extra train indicator

## Configuration Options

- `station_from`: Departure station (ID)
- `station_to`: Arrival station (ID)
- `exclude_vias`: Boolean - Exclude connections with transfers (default: false)
- `show_on_map`: Boolean - Include GPS coordinates in sensor attributes (default: false)

## API Integration

- Use pyrail library to interact with iRail API
- API client should use Home Assistant's aiohttp session: `async_get_clientsession(hass)`
- Handle API unavailability gracefully with error logging
- Example:
  ```python
  from pyrail import iRail
  from homeassistant.helpers.aiohttp_client import async_get_clientsession
  
  api_client = iRail(session=async_get_clientsession(hass))
  ```

## Error Handling

- Log errors using `_LOGGER.error()` for critical failures
- Use custom exception classes that inherit from `HomeAssistantError`
- Validate API responses before using data
- Return `False` from setup functions on critical errors

## Documentation

- Update README.md for user-facing changes
- Update CONTRIBUTING.md for developer workflow changes
- Include docstrings for public functions and classes
- Keep documentation concise and focused on practical usage

## Pull Request Guidelines

1. Run linting before submitting: `scripts/lint`
2. Run tests: `pytest tests/belgiantrain/`
3. Update documentation if behavior changes
4. Keep changes focused and minimal
5. Test locally using `scripts/develop`

## Common Patterns to Follow

### Async Functions
- All integration functions should be async
- Use `await` for API calls and Home Assistant operations

### Logging
```python
import logging

_LOGGER = logging.getLogger(__name__)
_LOGGER.error("Error message")
_LOGGER.warning("Warning message")
_LOGGER.debug("Debug message")
```

### Constants
- Define all magic strings and numbers in `const.py`
- Use `Final` type hint for constants
- Example: `DOMAIN: Final = "belgiantrain"`

## Testing Best Practices

- Mock all external API calls
- Test both success and failure scenarios
- Use pytest fixtures for common test setup
- Test config flow validation
- Test sensor state updates
- Verify sensor attributes are correct

## Home Assistant Integration Standards

- Follow Home Assistant quality scale requirements (see `quality_scale.yaml`)
- Use Home Assistant's built-in helper functions
- Implement proper config entry lifecycle (setup, unload)
- Support multiple config entries for different station pairs
- Use appropriate Home Assistant constants from `homeassistant.const`

## Security Considerations

- Never commit API keys or secrets
- Validate all user inputs in config flow
- Handle API rate limiting appropriately
- Use secure HTTPS connections to API

## Maintenance

- Keep dependencies up to date in `manifest.json` and `requirements.txt`
- Monitor Home Assistant core changes that may affect integration
- Update to latest pyrail library version when available
- Test with latest Home Assistant releases
