# ONVIF Integration Testing Guide

This guide explains how to test the ONVIF camera integration functionality.

---

## Prerequisites

1. **Python dependencies installed:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Backend server running:**
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

3. **Either:**
   - A physical ONVIF-compliant IP camera on your network, OR
   - An ONVIF camera simulator

---

## Testing with Real ONVIF Camera

### Step 1: Verify Camera is ONVIF-Compliant

Most modern IP cameras support ONVIF. Supported brands include:
- Hanwha (Samsung)
- Axis
- Hikvision
- Dahua
- Uniview
- Bosch
- Sony

Check your camera's manual or web interface to confirm ONVIF support.

### Step 2: Enable ONVIF on Camera

1. Log into camera web interface
2. Navigate to Network → ONVIF settings
3. Enable ONVIF
4. Set authentication: usually HTTP Digest or WS-UsernameToken
5. Note the ONVIF port (usually 80 or 8080)

### Step 3: Find Camera IP

Option A: Check your router's DHCP client list
Option B: Use network scanner:
```bash
# Windows
arp -a

# Linux/Mac
nmap -sn 192.168.1.0/24
```

### Step 4: Test Discovery

**Via Swagger UI:**
1. Open http://localhost:8000/docs
2. Click GET `/api/discover`
3. Click "Try it out"
4. Set timeout to 10 seconds
5. Click "Execute"

Expected response:
```json
{
  "cameras": [
    {
      "id": "onvif-192.168.1.100",
      "ip": "192.168.1.100",
      "port": 80,
      "name": "Camera-192.168.1.100",
      "manufacturer": "Hanwha",
      "model": "QNV-7080R",
      "scopes": [...],
      "discovered_at": "2025-12-06T..."
    }
  ],
  "scanDuration": 10,
  "foundCameras": 1
}
```

**Via cURL:**
```bash
curl "http://localhost:8000/api/discover?timeout=10"
```

### Step 5: Test Capabilities Query

**Via Swagger UI:**
1. Open http://localhost:8000/docs
2. Click GET `/api/cameras/{camera_id}/capabilities`
3. Click "Try it out"
4. Fill in:
   - camera_id: `test-cam-01`
   - ip: `192.168.1.100` (your camera IP)
   - port: `80`
   - username: `admin` (your camera username)
   - password: `yourpassword` (your camera password)
5. Click "Execute"

Expected response:
```json
{
  "cameraId": "test-cam-01",
  "capabilities": {
    "device": {
      "manufacturer": "Hanwha",
      "model": "QNV-7080R",
      "firmware": "2.40",
      "serial": "ABC123",
      "hardware_id": "XYZ789",
      "capabilities": {
        "analytics": false,
        "device": true,
        "events": true,
        "imaging": true,
        "media": true,
        "ptz": false
      }
    },
    "video_encoders": [
      {
        "name": "MainStream",
        "token": "VideoEncoder_1",
        "resolution": {
          "width": 1920,
          "height": 1080
        },
        "quality": 4,
        "fps": 30,
        "encoding": "H264",
        "bitrate_limit": 6000
      }
    ],
    "max_resolution": "1920x1080",
    "supported_codecs": ["H.264", "H.265"],
    "max_fps": 30
  }
}
```

### Step 6: Test Current Settings Query

**Via Swagger UI:**
1. Click GET `/api/cameras/{camera_id}/current-settings`
2. Fill in same parameters as capabilities query
3. Click "Execute"

Expected response:
```json
{
  "cameraId": "test-cam-01",
  "currentSettings": {
    "stream": {
      "resolution": "1920x1080",
      "codec": "H264",
      "fps": 30,
      "bitrateMbps": 6.0
    },
    "exposure": {
      "shutter": "Auto",
      "iris": "Auto",
      "wdr": "Unknown"
    },
    "lowLight": {
      "irMode": "Auto",
      "noiseReduction": "Unknown"
    },
    "queried_at": "2025-12-06T..."
  }
}
```

### Step 7: Test Settings Apply

**IMPORTANT:** This will modify your camera settings! Test on a non-production camera first.

**Via Swagger UI:**
1. Click POST `/api/apply`
2. Click "Try it out"
3. Paste this request body (adjust IP and credentials):

```json
{
  "camera": {
    "id": "test-cam-01",
    "ip": "192.168.1.100",
    "vendor": "Hanwha",
    "model": "QNV-7080R"
  },
  "settings": {
    "stream": {
      "resolution": "1920x1080",
      "codec": "H.265",
      "fps": 20,
      "bitrateMbps": 3.5,
      "keyframeInterval": 40
    },
    "exposure": {
      "shutter": "1/250"
    },
    "lowLight": {
      "irMode": "Auto"
    }
  },
  "applyVia": "onvif",
  "credentials": {
    "username": "admin",
    "password": "yourpassword",
    "port": 80
  },
  "verifyAfterApply": true
}
```

4. Click "Execute"

Expected response:
```json
{
  "job_id": "apply-test-cam-01-1733500000",
  "camera_id": "test-cam-01",
  "status": "completed",
  "progress": 100,
  "steps": [
    {"name": "Connect to camera", "status": "completed"},
    {"name": "Query current configuration", "status": "completed"},
    {"name": "Apply stream settings", "status": "completed"},
    {"name": "Apply imaging settings", "status": "skipped"},
    {"name": "Verify applied settings", "status": "completed"}
  ],
  "started_at": "2025-12-06T...",
  "completed_at": "2025-12-06T...",
  "result": {
    "applied_settings": {...},
    "verification_status": "success"
  }
}
```

### Step 8: Check Apply Job Status

**Via Swagger UI:**
1. Click GET `/api/apply/status/{job_id}`
2. Enter job_id from previous response
3. Click "Execute"

---

## Testing with ONVIF Camera Simulator

If you don't have a physical camera, use an ONVIF simulator:

### Option 1: ONVIF Device Test Tool (Windows)

1. Download from: https://www.onvif.org/profiles/conformance/test-tool/
2. Run the ONVIF Device Test Tool
3. Use built-in camera simulator
4. Test discovery and configuration

### Option 2: Happy Time ONVIF Server (Windows/Linux)

1. Download from: http://www.happytimesoft.com/products/onvif-server/
2. Configure virtual camera
3. Set IP and credentials
4. Test with CamOpt AI

### Option 3: Docker ONVIF Simulator

```bash
# Pull ONVIF simulator image
docker pull oznu/onvif-camera-simulator

# Run simulator
docker run -d \
  --name onvif-sim \
  -p 8080:8080 \
  oznu/onvif-camera-simulator

# Simulator will be available at:
# IP: 127.0.0.1
# Port: 8080
# Username: admin
# Password: admin
```

Test discovery:
```bash
curl "http://localhost:8000/api/discover?timeout=10"
```

---

## Troubleshooting

### Discovery finds no cameras

**Possible causes:**
1. Camera ONVIF not enabled → Enable in camera web interface
2. Camera on different subnet → Ensure camera and server on same network
3. Firewall blocking → Disable firewall temporarily to test
4. Wrong ONVIF port → Check camera documentation (try 80, 8080, 8000)

**Debug:**
```python
# Run discovery test directly
cd backend
python -c "from integrations.onvif_client import test_discovery; import asyncio; asyncio.run(test_discovery())"
```

### Connection timeout

**Possible causes:**
1. Wrong IP address
2. Camera offline
3. Firewall blocking port
4. Wrong credentials

**Test connectivity:**
```bash
# Ping camera
ping 192.168.1.100

# Test port
telnet 192.168.1.100 80
```

### Authentication failed

**Possible causes:**
1. Wrong username/password
2. Camera requires HTTP Digest auth (should work)
3. Camera ONVIF authentication disabled

**Solution:**
- Verify credentials in camera web interface
- Try default credentials (admin/admin, admin/12345)
- Check camera ONVIF authentication settings

### "WSDiscovery not available"

**Cause:** WSDiscovery package not installed

**Solution:**
```bash
pip install WSDiscovery==2.0.0
```

### "No video encoder configurations found"

**Possible causes:**
1. Camera doesn't support ONVIF media service
2. Camera requires specific profile selection
3. Camera ONVIF implementation incomplete

**Solution:**
- Check camera ONVIF compliance level (need Profile S for streaming)
- Try different ONVIF port
- Update camera firmware

### Settings not applying

**Possible causes:**
1. Camera doesn't support requested codec (e.g., H.265)
2. Resolution not supported
3. FPS/bitrate out of range
4. Camera requires reboot after config change

**Debug:**
```python
# Check what camera supports
# Query capabilities endpoint first
# Adjust settings to match supported values
```

---

## Supported ONVIF Operations

### ✅ Currently Implemented

- **Discovery:**
  - WS-Discovery camera scan
  - Parse manufacturer, model, IP
  - Device information query

- **Settings Query:**
  - GetVideoEncoderConfigurations
  - Get current stream settings (resolution, codec, FPS, bitrate)

- **Settings Apply:**
  - SetVideoEncoderConfiguration
  - Modify resolution, codec, FPS, bitrate, keyframe interval

### ⚠️ Partially Implemented

- **Imaging Settings:**
  - GetImagingSettings (implemented)
  - SetImagingSettings (implemented but needs video source token)
  - Exposure, WDR, backlight compensation

### ❌ Not Yet Implemented

- **PTZ Control:**
  - Pan/tilt/zoom commands
  - Preset positions

- **Events:**
  - Motion detection events
  - Analytics events

- **Analytics:**
  - Line crossing
  - Object detection

---

## Vendor-Specific Notes

### Hanwha (Samsung)

- ONVIF port: Usually 80
- Supports H.264 and H.265
- Excellent ONVIF compliance
- May require "ONVIF User" created in web interface

### Axis

- ONVIF port: Usually 80
- Full ONVIF Profile S and T support
- Supports advanced imaging settings
- May require ONVIF enabled in System Options

### Hikvision

- ONVIF port: Usually 80 or 8000
- Supports H.264 and H.265
- Some models have ONVIF compliance issues
- Firmware updates recommended

### Dahua

- ONVIF port: Usually 80
- Good ONVIF support on newer models
- Older models may have limited ONVIF features

---

## Next Steps

Once ONVIF integration is working:

1. **Integrate with optimization flow:**
   - Query current settings via ONVIF
   - Pass to Claude Vision for optimization
   - Apply optimized settings back to camera

2. **Add database persistence:**
   - Store discovered cameras
   - Track optimization history
   - Log applied configurations

3. **Build UI for camera management:**
   - Discovery page
   - Camera inventory
   - Apply confirmation dialogs

4. **Add monitoring:**
   - Periodic snapshot capture
   - Settings drift detection
   - Health metrics

---

## Additional Resources

- **ONVIF Specifications:** https://www.onvif.org/specs/
- **ONVIF Test Tool:** https://www.onvif.org/profiles/conformance/test-tool/
- **onvif-zeep Documentation:** https://github.com/FalkTannhaeuser/python-onvif-zeep
- **Zeep Documentation:** https://docs.python-zeep.org/

---

**Last Updated:** 2025-12-06
**Status:** Phase 4 Implementation Complete
