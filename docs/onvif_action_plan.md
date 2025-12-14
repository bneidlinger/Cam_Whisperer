# ONVIF Integration Action Plan for PlatoniCam

Based on the comprehensive ONVIF technical report (2024-2025), this document outlines prioritized enhancements to our camera integration layer.

---

## Executive Summary

Our current implementation uses basic Profile S patterns with WS-Discovery and RTSP. The report identifies several critical upgrades needed:

1. **Profile T Migration** (URGENT - Profile S deprecated Oct 2025)
2. **WebRTC Support** for low-latency live view
3. **MQTT Event Integration** (Profile M) for real-time analytics
4. **Security Hardening** (TLS, better auth)
5. **Performance Optimization** (WSDL caching, async operations)

---

## Phase 1: Foundation Improvements (Immediate)

### 1.1 Fix WS-Discovery Issues
**Status:** Partially done (warning suppression)
**Priority:** High

**Current Problem:**
- ResourceWarning spam from unclosed sockets
- No scope filtering causes broadcast storms on large networks
- Security vulnerability (unauthenticated UDP enumeration)

**Actions:**
```python
# backend/integrations/onvif_client.py

# 1. Add scope-based filtering to reduce broadcast traffic
def _discover_services(self, timeout: int, scopes: List[str] = None) -> List:
    """Filter discovery by scope to prevent broadcast storms"""
    wsd = WSDiscovery()
    wsd.start()
    try:
        if scopes:
            # Filter for specific locations/types
            services = wsd.searchServices(
                scopes=scopes,
                timeout=timeout
            )
        else:
            services = wsd.searchServices(timeout=timeout)
        return services
    finally:
        wsd.stop()

# 2. Add "Direct Connect" mode bypassing discovery entirely
async def connect_direct(self, ip: str, port: int, username: str, password: str):
    """Connect directly when IP is known - more secure than discovery"""
    # Skip WS-Discovery, connect directly to device service
    pass
```

**Files to Modify:**
- `backend/integrations/onvif_client.py`
- `backend/services/discovery.py`

---

### 1.2 WSDL Caching for Performance
**Priority:** High

**Current Problem:**
- `zeep` parses WSDL on every connection (5-10 second delay)
- Impacts user experience when connecting cameras

**Actions:**
```python
# backend/integrations/onvif_client.py

from zeep import Client
from zeep.cache import SqliteCache
from zeep.transports import Transport

class ONVIFClient:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        # Add WSDL caching - reduces connection time to milliseconds
        self.cache = SqliteCache(path='./wsdl_cache.db', timeout=86400)
        self.transport = Transport(cache=self.cache, timeout=timeout)
```

**Estimated Impact:** Connection time reduced from ~5s to <500ms

---

### 1.3 Async SOAP Operations
**Priority:** Medium

**Current Problem:**
- Synchronous SOAP calls block the event loop
- Can't efficiently poll multiple cameras

**Actions:**
```python
# Use httpx as async transport for zeep
import httpx
from zeep.transports import AsyncTransport

class AsyncONVIFClient:
    """Async ONVIF client for concurrent camera operations"""

    async def get_capabilities_batch(self, cameras: List[dict]) -> List[dict]:
        """Query capabilities from multiple cameras concurrently"""
        tasks = [
            self._get_camera_caps(cam)
            for cam in cameras
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)
```

---

## Phase 2: Profile T Migration (Critical - Q1 2025)

### 2.1 Media2 Service Support
**Priority:** CRITICAL (Profile S deprecated Oct 2025)

**What Changes:**
| Feature | Profile S (Current) | Profile T (Required) |
|---------|--------------------|--------------------|
| WSDL | media.wsdl | media2.wsdl |
| Codecs | H.264, MJPEG | H.265, H.264, MJPEG |
| Transport | RTSP (insecure) | RTSPS (TLS encrypted) |
| Imaging | Vendor-specific | Standardized |

**Actions:**
```python
# backend/integrations/onvif_client.py

async def get_capabilities(self, camera: ONVIFCamera) -> Dict:
    """Query capabilities with Profile T priority"""
    device_mgmt = camera.create_devicemgmt_service()
    caps = await self._run_sync(device_mgmt.GetCapabilities)

    # Check for Media2 service (Profile T indicator)
    has_profile_t = caps.Media2 is not None if hasattr(caps, 'Media2') else False

    if has_profile_t:
        # Use Media2 service for H.265 and advanced features
        media2 = camera.create_media2_service()
        profiles = await self._run_sync(media2.GetProfiles)
        # ... Profile T specific handling
    else:
        # Fallback to Profile S (legacy)
        media = camera.create_media_service()
        # ... existing logic with deprecation warning
        logger.warning(f"Camera {camera.host} only supports Profile S (deprecated)")

    return {
        "profile_t_supported": has_profile_t,
        "h265_supported": has_profile_t,  # H.265 requires Profile T
        # ...
    }
```

### 2.2 H.265 Encoder Configuration
**Priority:** High

**Actions:**
```python
# Add H.265 configuration support
async def configure_h265_encoder(
    self,
    camera: ONVIFCamera,
    config_token: str,
    settings: Dict
) -> bool:
    """Configure H.265 encoder (Profile T only)"""
    media2 = camera.create_media2_service()

    config = await self._run_sync(
        media2.GetVideoEncoderConfiguration,
        {"ConfigurationToken": config_token}
    )

    # H.265 specific parameters
    if settings.get("codec") == "H.265":
        config.Encoding = "H265"
        if "gov_length" in settings:
            config.GovLength = settings["gov_length"]
        if "profile" in settings:
            config.H265.H265Profile = settings["profile"]  # Main, Main10, etc.

    await self._run_sync(
        media2.SetVideoEncoderConfiguration,
        {"Configuration": config, "ForcePersistence": True}
    )
    return True
```

### 2.3 RTSPS (Secure RTSP) Support
**Priority:** High

**Actions:**
```python
# backend/integrations/onvif_client.py

async def get_stream_uri(
    self,
    camera: ONVIFCamera,
    profile_token: str,
    secure: bool = True  # Default to secure
) -> str:
    """Get stream URI with RTSPS support"""
    media = camera.create_media_service()

    stream_setup = {
        "Stream": "RTP-Unicast",
        "Transport": {
            "Protocol": "HTTPS" if secure else "RTSP"  # HTTPS = RTSPS tunnel
        }
    }

    uri_response = await self._run_sync(
        media.GetStreamUri,
        {"StreamSetup": stream_setup, "ProfileToken": profile_token}
    )

    return uri_response.Uri  # Returns rtsps:// or rtsp://
```

---

## Phase 3: WebRTC Low-Latency Streaming (Q2 2025)

### 3.1 WebRTC Signaling Gateway
**Priority:** Medium-High

**Why:** Current snapshot/RTSP has 500ms-2s latency. WebRTC offers 100-300ms.

**Architecture:**
```
Browser <--WebSocket--> Backend Gateway <--WS/JSON-RPC--> Camera
                              |
                        SDP Offer/Answer
                        ICE Candidates
                              |
Browser <====== SRTP (Direct P2P or TURN relay) ======> Camera
```

**Actions:**
```python
# backend/integrations/webrtc_signaling.py (NEW FILE)

import asyncio
import websockets
import json

class ONVIFWebRTCGateway:
    """
    WebRTC signaling gateway per ONVIF spec (Version 24.06)
    Proxies JSON-RPC 2.0 messages between browser and camera
    """

    async def handle_browser_connection(self, websocket, camera_ip: str):
        """Handle browser WebSocket connection"""
        # Connect to camera's WebRTC endpoint
        camera_ws_url = f"wss://{camera_ip}/onvif/webrtc"

        async with websockets.connect(camera_ws_url, ssl=self.ssl_context) as camera_ws:
            # Proxy messages bidirectionally
            await asyncio.gather(
                self._proxy_to_camera(websocket, camera_ws),
                self._proxy_to_browser(camera_ws, websocket)
            )

    async def _proxy_to_camera(self, browser_ws, camera_ws):
        """Forward browser SDP offers to camera"""
        async for message in browser_ws:
            msg = json.loads(message)

            # Inject authentication if needed
            if msg.get("method") == "register":
                msg["params"]["auth"] = self._generate_auth_token()

            await camera_ws.send(json.dumps(msg))

    async def _proxy_to_browser(self, camera_ws, browser_ws):
        """Forward camera SDP answers to browser"""
        async for message in camera_ws:
            await browser_ws.send(message)
```

### 3.2 TURN Server Integration
**Priority:** Medium

**Why:** Required for remote viewing through NAT/firewalls

**Actions:**
- Deploy Coturn server or use cloud TURN (Twilio, Xirsys)
- Add TURN configuration to settings
- Frontend generates relay candidates

```python
# backend/config.py
class Settings(BaseSettings):
    # WebRTC TURN server configuration
    turn_server_url: str = ""  # e.g., "turn:turn.example.com:3478"
    turn_username: str = ""
    turn_credential: str = ""
```

---

## Phase 4: Profile M Analytics Integration (Q2-Q3 2025)

### 4.1 MQTT Event Broker
**Priority:** Medium

**Why:** Replace inefficient SOAP polling with push notifications

**Current:** PullPoint polling (high latency, high overhead)
**Target:** MQTT pub/sub (real-time, efficient)

**Actions:**
```python
# backend/integrations/mqtt_events.py (NEW FILE)

import paho.mqtt.client as mqtt

class ONVIFEventBridge:
    """
    Bridge ONVIF cameras to MQTT broker for real-time events
    Per Profile M specification
    """

    def __init__(self, broker_host: str, broker_port: int = 1883):
        self.client = mqtt.Client()
        self.client.on_message = self._handle_event
        self.broker_host = broker_host
        self.broker_port = broker_port

    async def configure_camera_mqtt(self, camera: ONVIFCamera, broker_config: dict):
        """Configure camera to publish events to MQTT broker"""
        event_service = camera.create_events_service()

        # AddEventBroker command (Profile M)
        await self._run_sync(
            event_service.AddEventBroker,
            {
                "EventBroker": {
                    "Address": f"mqtt://{broker_config['host']}:{broker_config['port']}",
                    "TopicPrefix": f"platonicam/{camera.host}",
                    "UserName": broker_config.get("username"),
                    "Password": broker_config.get("password"),
                }
            }
        )

    def _handle_event(self, client, userdata, msg):
        """Process incoming camera events"""
        payload = json.loads(msg.payload)

        # Example event structure from report:
        # {"Topic": "tns1:RuleEngine/CellMotionDetector/Motion",
        #  "UtcTime": "...", "Data": {"IsMotion": true}}

        if "Motion" in payload.get("Topic", ""):
            self._trigger_motion_alert(payload)
        elif "LineCrossing" in payload.get("Topic", ""):
            self._trigger_line_crossing_alert(payload)
```

### 4.2 Metadata Stream Parsing
**Priority:** Low-Medium

**Why:** Overlay bounding boxes on video for detected objects

**Actions:**
```python
# backend/integrations/metadata_parser.py (NEW FILE)

import xml.etree.ElementTree as ET

def parse_analytics_frame(xml_payload: str) -> dict:
    """
    Parse ONVIF analytics metadata frame
    Returns detected objects with normalized bounding boxes
    """
    root = ET.fromstring(xml_payload)

    objects = []
    for obj in root.findall(".//tt:Object", namespaces=ONVIF_NS):
        bbox = obj.find(".//tt:BoundingBox", namespaces=ONVIF_NS)
        obj_class = obj.find(".//tt:Class/tt:Type", namespaces=ONVIF_NS)

        objects.append({
            "id": obj.get("ObjectId"),
            "type": obj_class.text if obj_class is not None else "Unknown",
            "confidence": float(obj_class.get("Likelihood", 0)),
            "bbox": {
                # Normalized 0.0-1.0 coordinates
                "left": float(bbox.get("left")),
                "top": float(bbox.get("top")),
                "right": float(bbox.get("right")),
                "bottom": float(bbox.get("bottom")),
            }
        })

    return {
        "timestamp": root.get("UtcTime"),
        "objects": objects
    }
```

---

## Phase 5: Security Hardening (Ongoing)

### 5.1 TLS Certificate Validation
**Priority:** High

**Actions:**
```python
# Enforce TLS for all camera connections
import ssl

def create_secure_context() -> ssl.SSLContext:
    """Create TLS context for camera connections"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    # For self-signed certs in dev, add to trusted store
    return ctx
```

### 5.2 Disable WS-Discovery After Provisioning
**Priority:** Medium

**Why:** WS-Discovery is unauthenticated UDP - security risk

**Actions:**
- Add option to disable discovery on camera after initial setup
- Document security best practice in deployment guide

### 5.3 Media Signing Verification (Future)
**Priority:** Low (2026+)

**Why:** Tamper-evident video for legal admissibility

**Actions:**
- Parse SEI NAL units from H.264/H.265 streams
- Verify SHA-256 signatures against camera's public key
- Add "Verified" badge to exported clips

---

## Implementation Timeline

| Phase | Feature | Priority | Est. Effort | Status |
|-------|---------|----------|-------------|--------|
| 1.1 | WS-Discovery fixes | High | 2 days | ✅ DONE |
| 1.2 | WSDL caching | High | 1 day | ✅ DONE |
| 1.3 | Async operations | Medium | 3 days | ✅ DONE |
| 2.1 | Media2 service | Critical | 5 days | ✅ DONE |
| 2.2 | H.265 config | High | 2 days | ✅ DONE |
| 2.3 | RTSPS support | High | 2 days | ✅ DONE |
| 3.1 | WebRTC signaling | Medium | 1 week | ⏳ NOT STARTED |
| 3.2 | TURN integration | Medium | 3 days | ⏳ NOT STARTED |
| 4.1 | MQTT events | Medium | 1 week | ⏳ NOT STARTED |
| 4.2 | Metadata parsing | Low | 3 days | ⏳ NOT STARTED |
| 5.x | Security hardening | Ongoing | Continuous | 🔄 PARTIAL |

### Implementation Notes

**Phase 1 & 2 (Completed 2025-12-14):**
- WSDL caching implemented with SQLite at `backend/cache/wsdl_cache.db`
- Direct connect bypasses WS-Discovery when IP known
- Connection pooling reduces auth overhead
- Profile T detection with deprecation warnings for S-only cameras
- Media2Client created with full Profile S fallback
- H.265 config and RTSPS support integrated into ONVIFClient
- Tested with Hanwha QNV-C8011R (Profile S only - no H.265 via ONVIF)

**Phase 5 (Partial):**
- ResourceWarning suppression added
- TLS certificate validation not yet implemented
- WS-Discovery disable option not yet added

---

## Files to Create/Modify

### New Files:
| File | Purpose | Status |
|------|---------|--------|
| `backend/integrations/media2_client.py` | Profile T Media2 service | ✅ CREATED |
| `backend/integrations/webrtc_signaling.py` | WebRTC gateway | ⏳ TODO |
| `backend/integrations/mqtt_events.py` | MQTT event bridge | ⏳ TODO |
| `backend/integrations/metadata_parser.py` | Analytics metadata | ⏳ TODO |

### Modified Files:
| File | Changes | Status |
|------|---------|--------|
| `backend/integrations/onvif_client.py` | Caching, async, Profile T, H.265, RTSPS | ✅ DONE |
| `backend/services/discovery.py` | Scope filtering, direct connect, H.265 detection | ✅ DONE |
| `backend/main.py` | Warning suppression | ✅ DONE |
| `backend/start.bat` | PYTHONWARNINGS env var | ✅ DONE |
| `backend/start.ps1` | PYTHONWARNINGS env var | ✅ DONE |
| `backend/config.py` | TURN server, MQTT broker settings | ⏳ TODO |

---

## Dependencies to Add

```txt
# requirements.txt additions
zeep[async]>=4.2.0      # Async SOAP support
httpx>=0.25.0           # Async HTTP for zeep transport
aiortc>=1.6.0           # WebRTC for Python (optional, for server-side)
paho-mqtt>=2.0.0        # MQTT client
websockets>=12.0        # WebSocket for WebRTC signaling
```

---

## Testing Strategy

### Unit Tests:
- WSDL caching performance benchmarks
- Profile T detection logic
- Metadata XML parsing

### Integration Tests:
- Real camera Profile T configuration
- WebRTC signaling flow (mock camera)
- MQTT event delivery

### Hardware Tests:
- Hanwha QNV-C8011R (current test camera)
- Mix of Profile S-only and Profile T cameras
- H.265 encoding verification

---

## References

- ONVIF Core Specification 2.0
- ONVIF Profile T Specification
- ONVIF Profile M Specification
- ONVIF WebRTC Specification (Version 24.06)
- ONVIF Cloud Onboarding Specification (Version 25.06)
