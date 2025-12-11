# SNCB/NMBS Belgian Train Integration

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]

A Home Assistant custom integration for Belgian trains (SNCB/NMBS) with feature parity to the core Home Assistant NMBS integration.

## Features

This integration provides real-time train information from the iRail API (https://api.irail.be/):

- **Connection Sensors**: Monitor travel time between two stations, including:
  - Real-time departure and arrival information
  - Platform information for both departure and arrival
  - Delay information in minutes
  - Via connections with transfer details
  - Cancellation status
  - Vehicle ID
  - Optional map display with station coordinates

- **Liveboard Sensors**: View the next departures from any station (disabled by default):
  - Next train departure time
  - Destination station
  - Platform information
  - Delay information
  - Vehicle ID
  - Extra train indicator

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL
6. Select "Integration" as the category
7. Click "Add"
8. Search for "SNCB/NMBS" and install

### Manual Installation

1. Copy the `custom_components/belgiantrain` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "SNCB/NMBS"
4. Select your departure station from the dropdown
5. Select your arrival station from the dropdown
6. (Optional) Enable "Exclude via connections" to only show direct trains
7. (Optional) Enable "Show on map" to display station coordinates in sensor attributes

The integration will create:
- One main sensor showing the travel time in minutes between the two stations
- Two liveboard sensors (disabled by default) for each station showing the next departure

## Sensors

### Connection Sensor
Shows the total travel time in minutes between departure and arrival stations.

**Attributes:**
- `destination`: Destination station name
- `direction`: Direction name
- `platform_departing`: Departure platform
- `platform_arriving`: Arrival platform
- `vehicle_id`: Train vehicle ID
- `departure`: Human-readable departure time ("In X minutes")
- `departure_minutes`: Departure time in minutes
- `delay`: Delay information ("X minutes")
- `delay_minutes`: Delay in minutes
- `canceled`: Boolean indicating if train is canceled
- `via`: Via station name (if applicable)
- `via_arrival_platform`: Via station arrival platform (if applicable)
- `via_transfer_platform`: Via station departure platform (if applicable)
- `via_transfer_time`: Transfer time at via station in minutes (if applicable)
- `latitude`: Station latitude (if "Show on map" enabled)
- `longitude`: Station longitude (if "Show on map" enabled)

### Liveboard Sensors
Shows the next departure from a station.

**Attributes:**
- `departure`: Human-readable departure time ("In X minutes")
- `departure_minutes`: Departure time in minutes
- `extra_train`: Boolean indicating if this is an extra train
- `vehicle_id`: Train vehicle ID
- `monitored_station`: The station being monitored
- `delay`: Delay information (if applicable)
- `delay_minutes`: Delay in minutes (if applicable)

## Development

This repository contains multiple files for development:

File | Purpose
--- | ---
`custom_components/belgiantrain/` | Integration source code
`tests/belgiantrain/` | Integration tests
`scripts/` | Development scripts (setup, lint, develop)
`requirements.txt` | Python packages for development/testing

### Development Setup

1. Clone the repository
2. Run `scripts/setup` to install dependencies
3. Run `scripts/lint` to check code quality
4. Run `scripts/develop` to start Home Assistant for testing

### Running Tests

```bash
pytest tests/belgiantrain/
```

## Data Source

This integration uses the iRail API (https://api.irail.be/) which provides real-time Belgian train information from SNCB/NMBS.

## Credits

This integration achieves feature parity with the [core Home Assistant NMBS integration](https://github.com/home-assistant/core/tree/dev/homeassistant/components/nmbs).

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

[releases-shield]: https://img.shields.io/github/release/tjorim/belgiantrain.svg?style=for-the-badge
[releases]: https://github.com/tjorim/belgiantrain/releases
[license-shield]: https://img.shields.io/github/license/tjorim/belgiantrain.svg?style=for-the-badge
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
