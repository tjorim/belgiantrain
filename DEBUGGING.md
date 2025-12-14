# Debugging Guide: No Entities Created

If entities aren't appearing after setup, follow these steps:

## 1. Check Home Assistant Logs

Look for these log messages:

```bash
# Enable debug logging in configuration.yaml:
logger:
  default: info
  logs:
    custom_components.belgiantrain: debug
```

Then restart HA and check logs for:
- `"Setting up entry"` - Shows which entries are being set up
- `"Creating connection subentry"` or `"Creating liveboard subentry"` - Confirms subentries are created
- `"Forwarding entry setup to platforms"` - Confirms sensor platform is being called
- `"Sensor setup for entry"` - Shows sensor.py is being invoked
- `"No coordinator found"` - ERROR: Indicates coordinator wasn't created
- `"Aborting sensor setup"` - Identifies why entity creation failed

## 2. Verify Subentries Were Created

In Home Assistant UI:
1. Go to **Settings** → **Devices & Services**
2. Click on **SNCB/NMBS** integration
3. You should see:
   - Main entry: "SNCB/NMBS Belgian Trains"
   - Subentries: "Connection: Station A → Station B" and/or "Liveboard - Station X"

If subentries are missing, the issue is in `__init__.py` subentry creation logic.

## 3. Check Config Entry Data

Add this temporary debug code to `__init__.py` around line 286:

```python
_LOGGER.error(
    "DEBUG: Entry data after restart: %s, subentries: %s",
    entry.data,
    list(entry.subentries.keys()) if hasattr(entry, "subentries") else "N/A"
)
```

This shows what data the entry has on restart.

## 4. Common Issues & Fixes

### Issue: Main entry data is empty after restart
**Cause:** Cleanup removed all keys (lines 492-511 in __init__.py)
**Expected:** This is normal for HA 2025.2+ - subentries should exist independently
**Fix:** Verify subentries exist in UI

### Issue: "No coordinator found" error in logs
**Cause:** Coordinator wasn't created in `async_setup_entry`
**Check:**
- Is `subentry_type` correctly set?
- Did `async_config_entry_first_refresh()` succeed?
- Is API reachable?

### Issue: Sensor setup is skipped
**Cause:** Logic in sensor.py lines 100-105 skips main entry
**Expected:** Main entry SHOULD be skipped for HA 2025.2+
**Check:** Are subentries being processed by sensor.py?

### Issue: Subentries not created on initial setup
**Cause:** ConfigSubentry import failed or data structure wrong
**Fix:** Check logs for import errors or validation failures

## 5. Manual Test

Try adding a connection/liveboard manually:
1. Go to SNCB/NMBS integration
2. Click **ADD ENTRY**
3. Select "Connection" or "Liveboard"
4. Fill in stations
5. Check if entity appears

If this works, the issue is with initial setup data handling.

## 6. Nuclear Option: Delete & Recreate

If all else fails:
1. Remove the SNCB/NMBS integration completely
2. Delete `.storage/core.config_entries` entry for belgiantrain (backup first!)
3. Restart Home Assistant
4. Re-add the integration from scratch

This ensures clean state without old data interfering.

## Expected Entity Structure

After successful setup, you should see:

**Device:** SNCB/NMBS
**Entities under this device:**
- `sensor.sncb_nmbs_train_from_[station_a]_to_[station_b]` (Connection sensor)
- `sensor.sncb_nmbs_liveboard_[station_x]` (Liveboard sensor)

All entities should be grouped under ONE device called "SNCB/NMBS".
