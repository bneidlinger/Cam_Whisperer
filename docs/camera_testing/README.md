# Camera Testing Documentation

This directory contains test documentation for cameras that have been tested with PlatoniCam.

## Tested Cameras

| Manufacturer | Model | Status | Last Tested |
|--------------|-------|--------|-------------|
| Hanwha Techwin | [QNV-C8011R](./QNV-C8011R.md) | In Progress | 2025-12-13 |

## Testing Checklist

When testing a new camera, verify the following:

### 1. Discovery
- [ ] Camera detected via ONVIF WS-Discovery
- [ ] Camera detected via WAVE VMS (if applicable)
- [ ] MAC address extracted correctly
- [ ] Vendor identified from OUI

### 2. Capabilities Query
- [ ] Supported resolutions detected
- [ ] Supported codecs detected
- [ ] Max FPS detected
- [ ] WDR levels detected
- [ ] IR modes detected

### 3. Optimization
- [ ] Claude AI optimization works
- [ ] Heuristic fallback works
- [ ] Recommendations are sensible for scene type
- [ ] Warnings generated appropriately

### 4. Apply Settings (ONVIF)
- [ ] Stream settings apply successfully
- [ ] Exposure settings apply successfully
- [ ] Settings verification works
- [ ] Rollback on failure works

### 5. VMS Integration (if applicable)
- [ ] Camera visible in VMS discovery
- [ ] Settings apply through VMS API
- [ ] Verification through VMS works

## Adding New Camera Documentation

1. Create a new file: `<MODEL>.md`
2. Copy the template from an existing camera doc
3. Fill in specifications from datasheet
4. Run through testing checklist
5. Document any quirks or issues

## Common Issues

### Discovery Failures
- Check firewall allows UDP 3702 (WS-Discovery)
- Verify camera is on same subnet
- Some cameras require ONVIF to be enabled in settings

### Authentication Errors
- Default credentials vary by manufacturer
- Check camera label or documentation
- Some cameras require initial setup via web interface

### Apply Failures
- Not all settings are exposed via ONVIF
- Some cameras require specific profile selection
- Imaging settings may require VideoSourceConfiguration token

---

**Maintained by**: PlatoniCam Development Team
