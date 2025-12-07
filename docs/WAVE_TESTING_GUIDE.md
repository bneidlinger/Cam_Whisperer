# Hanwha WAVE Integration - Testing Guide

This guide will help you test the new Hanwha WAVE VMS integration.

---

## Prerequisites

Before testing, ensure you have:

1. **Backend Running:**
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

2. **Hanwha WAVE Server:**
   - WAVE server running and accessible
   - Know the server IP address (e.g., 192.168.1.100)
   - Have admin credentials

3. **Network Access:**
   - Backend can reach WAVE server on port 7001 (HTTPS)
   - Firewall allows outbound connections

---

## Quick Test (Recommended)

### Option 1: Automated Test Script

Run the comprehensive test script:

```powershell
cd backend
.\test_wave.ps1 -WaveServer "YOUR_WAVE_IP" -WaveUsername "admin" -WavePassword "YOUR_PASSWORD"
```

**Example:**
```powershell
.\test_wave.ps1 -WaveServer "192.168.1.100" -WaveUsername "admin" -WavePassword "admin123"
```

This will test:
- ✅ Camera discovery
- ✅ Camera capabilities query
- ✅ Current settings query
- ✅ Settings apply with job tracking

---

## Manual Testing

### Step 1: Check Backend is Running

```bash
curl http://localhost:8000/docs
```

You should see the Swagger UI. Look for new endpoints:
- `/api/wave/discover`
- `/api/wave/cameras/{camera_id}/capabilities`
- `/api/wave/cameras/{camera_id}/current-settings`

### Step 2: Test Camera Discovery

**Using curl:**
```bash
curl -X GET "http://localhost:8000/api/wave/discover?server_ip=192.168.1.100&username=admin&password=admin123"
```

**Using PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/wave/discover?server_ip=192.168.1.100&username=admin&password=admin123" -Method GET | ConvertTo-Json
```

**Expected Response:**
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
      "recording": true
    }
  ],
  "foundCameras": 1,
  "vmsSystem": "hanwha-wave"
}
```

### Step 3: Get Camera Capabilities

Using a camera ID from Step 2:

```bash
curl -X GET "http://localhost:8000/api/wave/cameras/camera-001/capabilities?server_ip=192.168.1.100&username=admin&password=admin123"
```

### Step 4: Get Current Settings

```bash
curl -X GET "http://localhost:8000/api/wave/cameras/camera-001/current-settings?server_ip=192.168.1.100&username=admin&password=admin123"
```

### Step 5: Apply Settings (Optional - Modifies Camera!)

**⚠️ Warning:** This will modify your camera settings!

```bash
curl -X POST "http://localhost:8000/api/apply" \
  -H "Content-Type: application/json" \
  -d '{
    "camera": {
      "id": "test-cam-01",
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

---

## Testing Without a Real WAVE Server

If you don't have access to a WAVE server, you can still test the code:

### 1. Check Code Syntax

```bash
cd backend
python -c "from integrations.hanwha_wave_client import HanwhaWAVEClient; print('✅ Import successful')"
python -c "from services.discovery import DiscoveryService; print('✅ Discovery service OK')"
python -c "from services.apply import ApplyService; print('✅ Apply service OK')"
```

### 2. Check API Documentation

Visit: http://localhost:8000/docs

Look for these new endpoints in the Swagger UI:
- `GET /api/wave/discover`
- `GET /api/wave/cameras/{camera_id}/capabilities`
- `GET /api/wave/cameras/{camera_id}/current-settings`

### 3. Test Error Handling

Try connecting to a non-existent server:

```bash
curl -X GET "http://localhost:8000/api/wave/discover?server_ip=1.1.1.1&username=admin&password=test"
```

You should get a proper error response (not a crash).

---

## Troubleshooting

### Backend Won't Start

**Error:** `ModuleNotFoundError: No module named 'integrations.hanwha_wave_client'`

**Solution:**
```bash
# Make sure you're in the backend directory
cd backend

# Restart the server
uvicorn main:app --reload
```

### Connection Timeout to WAVE Server

**Error:** `Connection timeout to https://192.168.1.100:7001`

**Check:**
1. WAVE server is running: `ping 192.168.1.100`
2. Port 7001 is open: `telnet 192.168.1.100 7001`
3. Firewall allows connection
4. Server IP is correct

### Authentication Failed

**Error:** `Authentication failed - invalid credentials`

**Check:**
1. Username and password are correct
2. User has API access in WAVE
3. User is not locked out
4. Try with the admin account

### SSL Certificate Error

**Note:** This should NOT happen (self-signed certs are automatically allowed)

If you see SSL errors:
- Check `verify_ssl=False` in the WAVE client
- Update `urllib3` if needed

### Camera Not Found

**Error:** `Camera {id} not found`

**Solution:**
1. Use the exact camera ID from discovery
2. Verify camera exists in WAVE UI
3. Check camera is enabled

---

## Expected Test Results

### Successful Discovery

```
✅ PASS : WAVE Camera Discovery (2.3s)
  Found 5 cameras
  - Front Entrance (Hanwha QNV-7080R) at 192.168.1.10
  - Back Door (Axis P3245-LVE) at 192.168.1.11
  ...
```

### Successful Capabilities Query

```
✅ PASS : Get WAVE Camera Capabilities (1.5s)
  Device: Hanwha QNV-7080R
  Max Resolution: 3840x2160
  Max FPS: 30
```

### Successful Settings Apply

```
✅ PASS : Apply Settings via WAVE VMS (8.2s)
  Job: apply-wave-cam-01-1733500000
  Status: completed

  Steps completed:
    ✓ Connect to WAVE server - completed
    ✓ Query current settings - completed
    ✓ Apply settings to camera - completed
    ✓ Verify applied settings - completed
    ✓ Apply complete - completed
```

---

## Performance Benchmarks

Typical response times (with good network):

| Operation | Expected Time |
|-----------|---------------|
| Discovery | 2-5 seconds |
| Capabilities | 1-2 seconds |
| Current Settings | 1-2 seconds |
| Apply Settings | 5-10 seconds |

If times are significantly longer:
- Check network latency to WAVE server
- Verify WAVE server is not overloaded
- Check number of cameras (more = slower)

---

## Next Steps After Testing

### If Tests Pass ✅

1. Test end-to-end workflow:
   - Discover → Query → Optimize → Apply
2. Test with multiple cameras
3. Test with different camera models
4. Document any limitations found

### If Tests Fail ❌

1. Check error messages in backend logs
2. Verify WAVE server version (4.0+ required)
3. Try with different WAVE server
4. Report issues with:
   - Error message
   - WAVE server version
   - Camera model/manufacturer
   - Network configuration

---

## Production Readiness Checklist

Before deploying to production:

- [ ] Tested with real WAVE server
- [ ] Tested with multiple camera types
- [ ] Verified settings apply correctly
- [ ] Tested error handling
- [ ] Reviewed security (credentials, SSL)
- [ ] Load tested with expected number of cameras
- [ ] Documented WAVE server requirements
- [ ] Created user guide for operators

---

## Support

**Documentation:**
- Full integration guide: `backend/WAVE_INTEGRATION.md`
- API specification: `backend/API_SPECIFICATION.md`

**Test Scripts:**
- Automated tests: `backend/test_wave.ps1`
- ONVIF tests (for comparison): `backend/test_onvif.ps1`

**Code:**
- WAVE client: `backend/integrations/hanwha_wave_client.py`
- Discovery service: `backend/services/discovery.py`
- Apply service: `backend/services/apply.py`

---

**Happy Testing! 🧪**
