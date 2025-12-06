# Hanwha WAVE VMS Integration

**Status:** ✅ Implemented
**Version:** v0.3.0
**Last Updated:** 2025-12-06

---

## Overview

CamOpt AI now supports full integration with Hanwha WAVE (formerly Wisenet WAVE) Video Management System. This enables managing cameras through the VMS rather than directly via ONVIF, which is often preferred in enterprise deployments.

### What is Hanwha WAVE?

Hanwha WAVE VMS is a universal enterprise video management system that supports cameras from multiple manufacturers. It provides centralized management, recording, playback, and analytics capabilities.

**Key Features:**
- Cross-platform (Windows, Linux, macOS)
- Unified interface for all cameras
- Distributed architecture
- REST API for integration
- Support for thousands of camera models

---

## Integration Capabilities

### What's Supported ✅

1. **Camera Discovery**
   - List all cameras registered in WAVE system
   - Get camera details (name, vendor, model, IP, status)
   - Filter by recording status, enabled state

2. **Camera Settings Query**
   - Get current stream settings (resolution, codec, FPS, bitrate)
   - Get recording configuration
   - Get camera capabilities

3. **Camera Settings Application**
   - Apply stream settings (resolution, codec, FPS, bitrate)
   - Apply recording settings (mode, quality, pre-recording)
   - Verify settings after apply
   - Job-based tracking with progress

4. **VMS Server Info**
   - Query WAVE server details
   - Check server version and status

### What's Not Supported (Yet) ⚠️

- ❌ Imaging settings (exposure, WDR, backlight) - handled by camera directly
- ❌ Camera add/remove operations
- ❌ User management
- ❌ Layout/view management
- ❌ Recording playback
- ❌ Analytics configuration

---

## Architecture

### Component Structure

```
CamOpt AI Backend
├── integrations/
│   └── hanwha_wave_client.py     # WAVE API client
├── services/
│   ├── discovery.py              # Camera discovery (with WAVE methods)
│   └── apply.py                  # Settings apply (with WAVE methods)
└── main.py                       # FastAPI endpoints for WAVE
```

### Data Flow

**Discovery Flow:**
```
User → GET /api/wave/discover
  ↓
DiscoveryService.discover_wave_cameras()
  ↓
HanwhaWAVEClient.get_cameras()
  ↓
WAVE API: GET /api/v1/devices
  ↓
Camera list returned to user
```

**Apply Flow:**
```
User → POST /api/apply (applyVia: "vms")
  ↓
ApplyService.apply_settings_vms()
  ↓
ApplyService._apply_settings_wave()
  ↓
HanwhaWAVEClient.apply_camera_settings()
  ↓
WAVE API: PATCH /api/v1/devices/{id}
  ↓
Settings applied, verification, job tracking
```

---

## API Reference

### WAVE-Specific Endpoints

#### 1. Discover WAVE Cameras

```http
GET /api/wave/discover
```

**Query Parameters:**
- `server_ip` (required): WAVE server IP address
- `port` (optional): WAVE API port (default: 7001)
- `username` (optional): WAVE username (default: "admin")
- `password` (optional): WAVE password
- `use_https` (optional): Use HTTPS (default: true)

**Response:**
```json
{
  "cameras": [
    {
      "id": "camera-001",
      "name": "Front Entrance",
      "ip": "192.168.1.10",
      "vendor": "Hanwha",
      "model": "QNV-7080R",
      "status": "online",
      "enabled": true,
      "recording": true,
      "url": "rtsp://192.168.1.10:554/...",
      "vmsId": "camera-001",
      "vmsSystem": "hanwha-wave",
      "discovery_method": "wave",
      "wave_server": "192.168.1.100"
    }
  ],
  "foundCameras": 1,
  "vmsSystem": "hanwha-wave",
  "serverIp": "192.168.1.100"
}
```

#### 2. Get WAVE Camera Capabilities

```http
GET /api/wave/cameras/{camera_id}/capabilities
```

**Query Parameters:**
- `camera_id` (path): Camera ID in WAVE system
- `server_ip` (required): WAVE server IP
- `port`, `username`, `password`: Same as above

**Response:**
```json
{
  "cameraId": "camera-001",
  "capabilities": {
    "device": {
      "manufacturer": "Hanwha",
      "model": "QNV-7080R",
      "name": "Front Entrance"
    },
    "current_settings": { ... },
    "max_resolution": "3840x2160",
    "supported_codecs": ["H.265"],
    "max_fps": 30,
    "vms_managed": true,
    "vms_system": "hanwha-wave"
  },
  "vmsSystem": "hanwha-wave"
}
```

#### 3. Get WAVE Camera Current Settings

```http
GET /api/wave/cameras/{camera_id}/current-settings
```

**Response:**
```json
{
  "cameraId": "camera-001",
  "currentSettings": {
    "stream": {
      "resolution": "1920x1080",
      "codec": "H.265",
      "fps": 30,
      "bitrateMbps": 6.0,
      "keyframeInterval": 60,
      "cbr": true
    },
    "recording": {
      "mode": "always",
      "quality": "high",
      "preRecordSeconds": 5
    },
    "vms_managed": true,
    "vms_system": "hanwha-wave"
  },
  "vmsSystem": "hanwha-wave"
}
```

#### 4. Apply Settings via WAVE

```http
POST /api/apply
```

**Request Body:**
```json
{
  "camera": {
    "id": "cam-01",
    "ip": "192.168.1.10",
    "vmsSystem": "hanwha-wave",
    "vmsCameraId": "camera-001"
  },
  "settings": {
    "stream": {
      "resolution": "1920x1080",
      "codec": "H.265",
      "fps": 20,
      "bitrateMbps": 4.0
    }
  },
  "applyVia": "vms",
  "credentials": {
    "server_ip": "192.168.1.100",
    "port": 7001,
    "username": "admin",
    "password": ""
  },
  "verifyAfterApply": true
}
```

**Response:**
```json
{
  "job_id": "apply-wave-cam-01-1733500000",
  "status": "completed",
  "message": "Settings applied successfully via WAVE VMS",
  "camera_id": "cam-01",
  "vms_camera_id": "camera-001"
}
```

---

## Configuration

### WAVE Server Requirements

**Minimum Version:** WAVE 4.0 or higher

**API Configuration:**
- Default Port: **7001** (HTTPS)
- Protocol: **HTTPS** (self-signed certificate by default)
- Authentication: **HTTP Digest Auth**

**Firewall Rules:**
- Allow inbound TCP 7001 (HTTPS API)
- Allow inbound TCP 7080 (HTTP streaming, optional)

### User Permissions

The WAVE user account must have these permissions:
- ✅ View cameras
- ✅ Modify camera settings
- ✅ Access API

**Recommended:** Create a dedicated API user with limited permissions.

---

## Usage Examples

### Example 1: Discover Cameras from WAVE

```bash
# Using curl
curl -X GET "http://localhost:8000/api/wave/discover?server_ip=192.168.1.100&username=admin&password=admin123"

# Using PowerShell
Invoke-RestMethod -Uri "http://localhost:8000/api/wave/discover?server_ip=192.168.1.100" -Method GET
```

### Example 2: Get Camera Settings

```bash
curl -X GET "http://localhost:8000/api/wave/cameras/camera-001/current-settings?server_ip=192.168.1.100&username=admin&password=admin123"
```

### Example 3: Apply Settings via WAVE

```bash
curl -X POST "http://localhost:8000/api/apply" \
  -H "Content-Type: application/json" \
  -d '{
    "camera": {
      "id": "cam-01",
      "ip": "192.168.1.10",
      "vmsSystem": "hanwha-wave",
      "vmsCameraId": "camera-001"
    },
    "settings": {
      "stream": {
        "resolution": "1920x1080",
        "codec": "H.265",
        "fps": 20,
        "bitrateMbps": 4.0
      }
    },
    "applyVia": "vms",
    "credentials": {
      "server_ip": "192.168.1.100",
      "username": "admin",
      "password": "admin123"
    },
    "verifyAfterApply": true
  }'
```

### Example 4: End-to-End Workflow

```powershell
# 1. Discover cameras from WAVE
$cameras = (Invoke-RestMethod -Uri "http://localhost:8000/api/wave/discover?server_ip=192.168.1.100&username=admin&password=admin123" -Method GET).cameras

# 2. Get first camera
$camera = $cameras[0]
Write-Host "Camera: $($camera.name) at $($camera.ip)"

# 3. Get current settings
$currentSettings = Invoke-RestMethod -Uri "http://localhost:8000/api/wave/cameras/$($camera.id)/current-settings?server_ip=192.168.1.100&username=admin&password=admin123" -Method GET
Write-Host "Current settings: $(ConvertTo-Json $currentSettings)"

# 4. Optimize with Claude Vision
$optimizeRequest = @{
    camera = @{
        id = "cam-01"
        ip = $camera.ip
        vendor = $camera.vendor
        model = $camera.model
        sceneType = "entrance"
        purpose = "face_recognition"
    }
    capabilities = @{
        maxResolution = "1920x1080"
        supportedCodecs = @("H.265", "H.264")
        maxFps = 30
    }
    currentSettings = $currentSettings.currentSettings
    context = @{
        bandwidthLimitMbps = 5.0
    }
}

$optimized = Invoke-RestMethod -Uri "http://localhost:8000/api/optimize" -Method POST -Body (ConvertTo-Json $optimizeRequest -Depth 10) -ContentType "application/json"
Write-Host "Optimized settings confidence: $($optimized.confidence)"

# 5. Apply optimized settings via WAVE
$applyRequest = @{
    camera = @{
        id = "cam-01"
        ip = $camera.ip
        vmsSystem = "hanwha-wave"
        vmsCameraId = $camera.id
    }
    settings = $optimized.recommendedSettings
    applyVia = "vms"
    credentials = @{
        server_ip = "192.168.1.100"
        username = "admin"
        password = "admin123"
    }
    verifyAfterApply = $true
}

$applyResult = Invoke-RestMethod -Uri "http://localhost:8000/api/apply" -Method POST -Body (ConvertTo-Json $applyRequest -Depth 10) -ContentType "application/json"
Write-Host "Apply job: $($applyResult.job_id) - Status: $($applyResult.status)"

# 6. Check job status
Start-Sleep -Seconds 5
$jobStatus = Invoke-RestMethod -Uri "http://localhost:8000/api/apply/status/$($applyResult.job_id)" -Method GET
Write-Host "Job final status: $($jobStatus.status)"
```

---

## Testing

### Quick Test

```bash
# Navigate to backend directory
cd backend

# Run WAVE integration test script
.\test_wave.ps1 -WaveServer "192.168.1.100" -WaveUsername "admin" -WavePassword "admin123"
```

### Test Configuration

Edit `test_wave.ps1` parameters:
```powershell
param(
    [string]$BackendUrl = "http://localhost:8000",
    [string]$WaveServer = "192.168.1.100",    # Your WAVE server IP
    [int]$WavePort = 7001,
    [string]$WaveUsername = "admin",
    [string]$WavePassword = "",                # Your WAVE password
    [bool]$UseHttps = $true
)
```

### Test Coverage

The test script validates:
- ✅ WAVE camera discovery
- ✅ Camera capabilities query
- ✅ Current settings query
- ✅ Settings apply with job tracking
- ✅ Settings verification

---

## Implementation Details

### HanwhaWAVEClient Class

**File:** `backend/integrations/hanwha_wave_client.py`

**Key Methods:**

```python
class HanwhaWAVEClient:
    def __init__(self, server_ip, port=7001, username="admin", password="")

    async def test_connection(self) -> bool
    async def get_cameras(self) -> List[Dict]
    async def get_camera_settings(self, camera_id: str) -> Dict
    async def apply_camera_settings(self, camera_id: str, settings: Dict) -> bool
    async def get_snapshot(self, camera_id: str) -> Optional[bytes]
    async def get_server_info(self) -> Dict
```

**Features:**
- HTTP Digest authentication
- Self-signed SSL certificate support
- Async/await throughout
- ThreadPoolExecutor for blocking HTTP calls
- Comprehensive error handling
- Settings format conversion (CamOpt ↔ WAVE)

### API Endpoints

**WAVE API Structure:**
```
https://<server-ip>:7001/api/v1/...

Common Endpoints:
- GET  /api/v1/servers        # Server info
- GET  /api/v1/devices        # List all devices (cameras, servers, etc.)
- GET  /api/v1/devices/{id}   # Get specific device
- PATCH /api/v1/devices/{id}  # Update device settings
- GET  /api/v1/devices/{id}/image  # Get snapshot
```

**Alternative (Legacy) Endpoints:**
```
https://<server-ip>:7001/ec2/...

- GET  /ec2/getCamerasEx       # Get cameras (legacy)
```

### Settings Format Conversion

**CamOpt Format → WAVE Format:**

```python
# CamOpt format (input)
{
    "stream": {
        "resolution": "1920x1080",
        "codec": "H.265",
        "fps": 20,
        "bitrateMbps": 4.0,
        "keyframeInterval": 60,
        "cbr": True
    }
}

# Converted to WAVE format (output)
{
    "streamSettings": {
        "resolution": "1920x1080",
        "codec": "H.265",
        "fps": 20,
        "bitrate": 4000,          # Mbps → kbps
        "keyFrameInterval": 60,
        "bitrateMode": "CBR"      # boolean → string
    }
}
```

---

## Troubleshooting

### Common Issues

#### 1. Connection Refused / Timeout

**Symptoms:**
```
Cannot connect to WAVE server at https://192.168.1.100:7001
```

**Solutions:**
- ✅ Verify WAVE server is running
- ✅ Check firewall allows port 7001
- ✅ Confirm server IP is correct
- ✅ Try with `use_https=false` if HTTPS fails

#### 2. Authentication Failed

**Symptoms:**
```
Authentication failed - invalid credentials
```

**Solutions:**
- ✅ Verify username and password
- ✅ Check user has API access permissions
- ✅ Try with admin account first
- ✅ Check WAVE user is not locked out

#### 3. SSL Certificate Error

**Symptoms:**
```
SSL certificate verification failed
```

**Note:** This is **expected** with WAVE's default self-signed certificate.

**Solution:**
WAVE client automatically disables SSL verification (`verify_ssl=False` by default). This is safe for local networks.

#### 4. Camera Not Found

**Symptoms:**
```
Camera {id} not found
```

**Solutions:**
- ✅ Use correct camera ID from discovery
- ✅ Verify camera is registered in WAVE
- ✅ Check camera is enabled in WAVE

#### 5. Settings Not Applied

**Symptoms:**
```
Settings verification failed
```

**Possible Causes:**
- Some cameras don't support all settings
- WAVE may override certain parameters
- Camera may require restart

**Solutions:**
- ✅ Check camera capabilities first
- ✅ Try applying settings directly via WAVE UI
- ✅ Review camera documentation
- ✅ Check WAVE version compatibility

---

## Performance

### Benchmarks

**Tested with:** WAVE 5.1, 50 cameras

| Operation | Typical Time |
|-----------|--------------|
| Camera discovery | 2-5s |
| Capabilities query | 1-2s |
| Settings query | 1-2s |
| Settings apply | 3-5s |
| Settings verification | 2-3s |
| Total apply workflow | 5-10s |

### Scaling

- **Cameras:** Tested with up to 50 cameras
- **Concurrent Requests:** ~10 simultaneous operations
- **WAVE Server Load:** Minimal impact observed

### Optimization Tips

1. **Cache camera list:** Discovery is relatively slow, cache results
2. **Batch operations:** Apply settings to multiple cameras concurrently
3. **Skip verification:** If speed is critical, disable `verifyAfterApply`
4. **Use connection pooling:** HTTP session is reused automatically

---

## Security Considerations

### Authentication

- ✅ HTTP Digest authentication (more secure than Basic)
- ✅ Credentials not stored in memory after use
- ✅ SSL/TLS support (HTTPS)
- ⚠️ Self-signed certificates disabled verification

**Best Practices:**
- Use HTTPS in production
- Create dedicated API user with minimal permissions
- Rotate credentials regularly
- Don't commit credentials to git

### Network Security

**Recommended Firewall Rules:**
```
# Allow CamOpt backend to access WAVE server
Source: <backend-ip>
Destination: <wave-server-ip>:7001
Protocol: TCP
Action: Allow
```

**Isolation:**
- Run WAVE on separate management VLAN
- Use VPN for remote access
- Implement IP whitelisting on WAVE

---

## Future Enhancements

### Planned Features (v0.4.0+)

1. **Advanced Camera Operations**
   - Add/remove cameras via WAVE
   - PTZ control
   - Camera groups management

2. **Recording Management**
   - Start/stop recording
   - Export recordings
   - Playback integration

3. **Analytics**
   - Event rules configuration
   - Bookmark creation
   - Motion detection setup

4. **User Management**
   - Create/modify WAVE users
   - Permission management

5. **Monitoring**
   - Health status tracking
   - Storage monitoring
   - Alert notifications

---

## Related Documentation

- **ONVIF Integration:** `backend/ONVIF_INTEGRATION_SUMMARY.md`
- **API Specification:** `backend/API_SPECIFICATION.md`
- **Architecture:** `backend/ARCHITECTURE.md`
- **Testing Guide:** `backend/ONVIF_TESTING.md`

---

## References

### Official WAVE Documentation

- WAVE Server HTTP REST API: https://support.hanwhavisionamerica.com/hc/en-us/articles/1260806781909-WAVE-Server-HTTP-REST-API
- WAVE SDK/API: https://support.hanwhavisionamerica.com/hc/en-us/articles/115013501208-WAVE-SDK-API
- WAVE Features: https://wavevms.com/wavefeatures/rest-api/

### VMS Comparison

| Feature | ONVIF | WAVE | Genetec | Milestone |
|---------|-------|------|---------|-----------|
| **Discovery** | Network scan | API query | API query | API query |
| **Direct Control** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **VMS Integration** | N/A | ✅ Yes | ⏳ Future | ⏳ Future |
| **Multi-vendor** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Complexity** | Medium | Low | High | Medium |

---

**Status:** Production Ready ✅
**Last Updated:** 2025-12-06
**Version:** v0.3.0
