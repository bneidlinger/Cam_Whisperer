# Hanwha QNV-C8011R/VEX Camera Testing

## Camera Specifications

| Field | Value |
|-------|-------|
| Manufacturer | Hanwha Techwin |
| Model | QNV-C8011R/VEX |
| Resolution | 4K (3840x2160) / 5MP / 1080p |
| Lens | Varifocal 2.8-12mm |
| IR Range | 30m |
| Form Factor | Vandal-resistant dome |
| ONVIF | Profile S, T |
| Codecs | H.265, H.264 |

## Test Environment

- **Date**: 2025-12-13
- **PlatoniCam Version**: 0.5.0 (unreleased)
- **Backend**: FastAPI on localhost:8000
- **Frontend**: Static served on localhost:3000

## Test Results

### Discovery (ONVIF WS-Discovery)

| Test | Status | Notes |
|------|--------|-------|
| Camera detected | PASS | Responds to WS-Discovery multicast |
| Metadata retrieved | PASS | Model, vendor, firmware visible |
| MAC address extracted | PASS | OUI matches Hanwha Techwin |

### Capabilities Query

| Capability | Detected | Notes |
|------------|----------|-------|
| Resolutions | 3840x2160, 2592x1944, 1920x1080 | Multiple stream profiles |
| Codecs | H.265, H.264 | Both supported |
| Max FPS | 30 | At 1080p |
| WDR | Off, Low, Medium, High | 4 levels |
| IR Modes | Off, Auto, On | Smart IR |
| LPR Mode | No | Not applicable for this model |

### Optimization

| Test | Status | Provider | Confidence | Time |
|------|--------|----------|------------|------|
| Parking scene | PASS | Claude | 0.80 | 17s |
| Lobby scene | PASS | Claude | 0.82 | 15s |
| Heuristic fallback | PASS | Heuristic | 0.60 | <1s |

**Sample Claude Recommendation (Parking):**
```json
{
  "stream": {
    "resolution": "1920x1080",
    "codec": "H.265",
    "fps": 30,
    "bitrateMbps": 7.5,
    "bitrateMode": "VBR"
  },
  "exposure": {
    "mode": "Auto",
    "wdr": "Medium",
    "shutter": "1/500",
    "gainLimit": "30dB"
  },
  "lowLight": {
    "irMode": "Auto",
    "dayNightMode": "Auto",
    "dnr": "Medium",
    "slowShutter": "Off"
  }
}
```

### Apply Settings (ONVIF)

| Test | Status | Notes |
|------|--------|-------|
| Stream settings | - | Not yet tested |
| Exposure settings | - | Not yet tested |
| Verification | - | Not yet tested |

## Known Issues

1. **Type coercion**: Claude sometimes returns string values like `"60"` for integer fields. Fixed with Pydantic validators in `main.py` (commit TBD).

## Configuration Notes

- Default ONVIF credentials: `admin` / (check camera label)
- ONVIF port: 80 (default)
- Web interface: `http://<camera-ip>/`

## Commands Used

```bash
# Start backend
cd backend
.\start.bat

# Run discovery
curl http://localhost:8000/api/discover?timeout=10

# Optimize camera
curl -X POST http://localhost:8000/api/optimize \
  -H "Content-Type: application/json" \
  -d '{"camera": {...}, "capabilities": {...}, "context": {...}}'
```

## Screenshots

(Add screenshots of web interface, optimization results, etc.)

---

**Last Updated**: 2025-12-13
**Tested By**: PlatoniCam Development
