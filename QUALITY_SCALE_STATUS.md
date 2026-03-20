# Integration Quality Scale Status

This document provides an overview of the Belgian Train (SNCB/NMBS) integration's current status against the [Home Assistant Integration Quality Scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/).

## Current Status Summary

| Tier | Status | Requirements Met | Notes |
|------|--------|------------------|-------|
| 🥉 **Bronze** | ✅ Complete | 18/19 (95%) | 1 exempt: brands (custom integration) |
| 🥈 **Silver** | ⚠️ Nearly Complete | 9/10 (90%) | 1 todo, 1 exempt |
| 🥇 **Gold** | ⚠️ In Progress | 8/22 (36%) | 9 todo, 5 exempt |
| 🏆 **Platinum** | ⚠️ Blocked | 2/3 (67%) | 1 todo (requires external dependency) |

## Detailed Status

### Bronze Tier ✅ (18/19 complete)

**Completed:**
- ✅ action-setup: Services registered in `async_setup`
- ✅ appropriate-polling: 1-minute polling interval in coordinators
- ✅ common-modules: Shared logic in coordinator.py, entity.py, const.py, data.py
- ✅ config-flow-test-coverage: Tests in test_config_flow.py
- ✅ config-flow: Full UI config flow
- ✅ dependency-transparency: pyrail documented in manifest.json and README
- ✅ docs-actions: Service actions documented in README
- ✅ docs-high-level-description: In README
- ✅ docs-installation-instructions: HACS and manual methods in README
- ✅ docs-removal-instructions: Standard HA removal applies
- ✅ entity-unique-id: All entities have unique IDs
- ✅ has-entity-name: BelgianTrainEntity sets `_attr_has_entity_name = True`
- ✅ runtime-data: Uses `entry.runtime_data` with BelgianTrainData
- ✅ test-before-configure: API tested in config flow
- ✅ test-before-setup: Station data validated before setup
- ✅ unique-config-entry: Single main entry enforced

**Exempt:**
- ⭕ brands: Custom integration (not in HA core)
- ⭕ entity-event-setup: Does not use events

---

### Silver Tier ⚠️ (9/10 complete)

**Completed:**
- ✅ action-exceptions: Services handle exceptions
- ✅ config-entry-unloading: `async_unload_entry` implemented
- ✅ docs-configuration-parameters: All params documented
- ✅ docs-installation-parameters: Installation params documented
- ✅ entity-unavailable: Via CoordinatorEntity
- ✅ integration-owner: @tjorim in manifest
- ✅ log-when-unavailable: Coordinator logs API errors
- ✅ test-coverage: 37 tests across 5 files

**Todo:**
- ❌ parallel-updates: `PARALLEL_UPDATES` not set in sensor.py

**Exempt:**
- ⭕ reauthentication-flow: No auth needed (public API)

---

### Gold Tier ⚠️ (8/22 complete)

**Completed:**
- ✅ diagnostics: Implemented in diagnostics.py
- ✅ docs-examples: Service examples in README
- ✅ docs-supported-functions: Documented in README
- ✅ docs-use-cases: In service documentation
- ✅ entity-disabled-by-default: Liveboard sensors disabled by default
- ✅ entity-translations: Translations in en, fr, de, nl

**Todo:**
- ❌ devices: No device entities created
- ❌ docs-data-update: Data update behavior not explicitly documented
- ❌ docs-known-limitations: Not documented
- ❌ docs-troubleshooting: No troubleshooting section
- ❌ entity-category: Entity categories not set
- ❌ entity-device-class: `SensorDeviceClass.DURATION` not set
- ❌ exception-translations: Not in strings.json
- ❌ icon-translations: Not in strings.json
- ❌ reconfiguration-flow: No options flow
- ❌ repair-issues: Not implemented

**Exempt:**
- ⭕ discovery: No discovery protocol (manual config)
- ⭕ discovery-update-info: No discovery
- ⭕ docs-supported-devices: API-based, not device integration
- ⭕ dynamic-devices: Not a device integration
- ⭕ stale-devices: Not a device integration

---

### Platinum Tier ⚠️ (2/3 complete)

**Completed:**
- ✅ async-dependency: pyrail is async (uses aiohttp)
- ✅ inject-websession: Passes `async_get_clientsession(hass)` to pyrail

**Todo:**
- ❌ strict-typing: Not in HA's `.strict-typing` file; pyrail may not be PEP-561 compliant

---

## Path to Platinum

To reach Platinum tier, we need to complete:

1. **1 Silver requirement**: PARALLEL_UPDATES
2. **10 Gold requirements**: devices, docs improvements, entity enhancements, reconfiguration flow
3. **1 Platinum requirement**: strict-typing (requires pyrail PEP-561 compliance)

**Total: 12 issues to address**

See [GitHub Issues](https://github.com/tjorim/belgiantrain/issues) for detailed tracking.

---

## References

- [Integration Quality Scale Rules](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/)
- [Quality Scale Checklist](https://developers.home-assistant.io/docs/core/integration-quality-scale/checklist/)
- [Quality Scale Overview](https://www.home-assistant.io/docs/quality_scale/)

---

*Last updated: Based on quality_scale.yaml analysis*
